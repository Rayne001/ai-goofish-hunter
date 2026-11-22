"""
Prompt 管理路由
"""
import os
import aiofiles
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from src.api.dependencies import get_task_service
from src.services.task_service import TaskService


router = APIRouter(prefix="/api/prompts", tags=["prompts"])

_PROMPTS_DIR = Path("prompts").resolve()


def _safe_prompt_path(filename: str) -> Path:
    """返回经过 containment 检查的绝对路径，防止任意 OS 上的路径穿越。"""
    try:
        resolved = (_PROMPTS_DIR / filename).resolve()
        resolved.relative_to(_PROMPTS_DIR)
    except (ValueError, OSError):
        raise HTTPException(status_code=400, detail="无效的文件名")
    return resolved


def _prompt_cleanup_enabled() -> bool:
    """Require an explicit opt-in before exposing Prompt deletion."""
    return os.getenv("PROMPT_CLEANUP_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _prompt_reference_path(value: str, prompts_dir: Path) -> Path | None:
    """Normalize a stored prompt reference without escaping the prompt root."""
    raw = str(value or "").strip().replace("\\", "/")
    if not raw:
        return None

    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        parts = candidate.parts
        if parts and parts[0] == "prompts":
            candidate = Path(*parts[1:])
        resolved = (prompts_dir / candidate).resolve()

    try:
        resolved.relative_to(prompts_dir)
    except (ValueError, OSError, RuntimeError):
        return None
    return resolved


def _list_orphan_prompt_candidates(prompts_dir: Path, tasks: list) -> list[dict]:
    """Return unreferenced task criteria files, excluding system templates."""
    root = prompts_dir.resolve()
    if not root.is_dir():
        return []

    protected_names = {"base_prompt.txt", "macbook_criteria.txt"}
    referenced_paths = set()
    for task in tasks:
        for field in ("ai_prompt_base_file", "ai_prompt_criteria_file"):
            reference = _prompt_reference_path(getattr(task, field, ""), root)
            if reference is not None:
                referenced_paths.add(reference)

    candidates = []
    for filepath in root.iterdir():
        if filepath.name in protected_names or not filepath.name.endswith("_criteria.txt"):
            continue
        if filepath.is_symlink() or not filepath.is_file():
            continue
        resolved = filepath.resolve()
        if resolved.parent != root or resolved in referenced_paths:
            continue

        stat = filepath.stat()
        candidates.append({
            "filename": filepath.name,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        })

    return sorted(candidates, key=lambda item: item["filename"].casefold())


class PromptUpdate(BaseModel):
    """Prompt 更新模型"""
    content: str


class PromptCleanupRequest(BaseModel):
    """用户在预览后显式选择的 Prompt 文件。"""
    filenames: list[str] = Field(min_length=1, max_length=100)


@router.get("")
async def list_prompts():
    """列出所有 prompt 文件"""
    if not _PROMPTS_DIR.is_dir():
        return []
    return [f for f in os.listdir(_PROMPTS_DIR) if f.endswith(".txt")]


@router.get("/orphans")
async def list_orphan_prompts(task_service: TaskService = Depends(get_task_service)):
    """List cleanup candidates only when the opt-in flag is enabled."""
    if not _prompt_cleanup_enabled():
        return {"enabled": False, "candidates": []}
    tasks = await task_service.get_all_tasks()
    return {
        "enabled": True,
        "candidates": _list_orphan_prompt_candidates(_PROMPTS_DIR, tasks),
    }


@router.delete("/orphans")
async def delete_orphan_prompts(
    request: PromptCleanupRequest,
    task_service: TaskService = Depends(get_task_service),
):
    """Delete only currently unreferenced task criteria files after explicit selection."""
    if not _prompt_cleanup_enabled():
        raise HTTPException(status_code=403, detail="Prompt 清理功能尚未启用")

    requested_names = list(dict.fromkeys(request.filenames))
    if any(
        not name
        or Path(name).name != name
        or not name.endswith("_criteria.txt")
        for name in requested_names
    ):
        raise HTTPException(status_code=400, detail="只能清理任务 criteria Prompt 文件")

    tasks = await task_service.get_all_tasks()
    candidates = {
        item["filename"]: item
        for item in _list_orphan_prompt_candidates(_PROMPTS_DIR, tasks)
    }
    no_longer_orphaned = [name for name in requested_names if name not in candidates]
    if no_longer_orphaned:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "部分文件已被引用或不再是可清理候选；请重新扫描",
                "filenames": no_longer_orphaned,
            },
        )

    root = _PROMPTS_DIR.resolve()
    paths = []
    for name in requested_names:
        original_path = root / name
        if original_path.is_symlink():
            raise HTTPException(status_code=409, detail=f"Prompt 文件状态已变化：{name}")
        filepath = _safe_prompt_path(name)
        if filepath != original_path or filepath.parent != root or not filepath.is_file():
            raise HTTPException(status_code=409, detail=f"Prompt 文件状态已变化：{name}")
        paths.append(filepath)

    deleted = []
    for filepath in paths:
        try:
            filepath.unlink()
            deleted.append(filepath.name)
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail={"message": "删除 Prompt 文件失败", "deleted": deleted, "error": str(exc)},
            )

    return {"deleted": deleted, "count": len(deleted)}


@router.get("/{filename}")
async def get_prompt(filename: str):
    """获取 prompt 文件内容"""
    filepath = _safe_prompt_path(filename)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Prompt 文件未找到")

    async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
        content = await f.read()
    return {"filename": filepath.name, "content": content}


@router.put("/{filename}")
async def update_prompt(
    filename: str,
    prompt_update: PromptUpdate,
):
    """更新 prompt 文件内容"""
    filepath = _safe_prompt_path(filename)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Prompt 文件未找到")

    try:
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(prompt_update.content)
        return {"message": f"Prompt 文件 '{filepath.name}' 更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写入文件时出错: {e}")

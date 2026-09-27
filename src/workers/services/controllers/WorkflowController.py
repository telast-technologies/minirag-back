import hashlib
import json
from celery import chain
from uuid import UUID

from src.config.settings import settings
from src.workers.celery_app import celery_app
from src.workers.tasks import process_assets_task, index_assets_task



class WorkflowController:
    
    @staticmethod
    def generate_deterministic_task_id(task_prefix: str, project_id: str, asset_ids: list[str]) -> str:
        sorted_assets = sorted([str(aid) for aid in asset_ids])
        payload = {
            "project_id": str(project_id),
            "asset_ids": sorted_assets,
        }
        payload_str = json.dumps(payload, sort_keys=True)
        task_hash = hashlib.md5(payload_str.encode()).hexdigest()
        return f"{task_prefix}-{task_hash}"

    @classmethod
    def trigger_process_and_index(
        cls, 
        project_id: UUID, 
        asset_ids: list[UUID], 
        chunk_size: int = settings.DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP
    ):
        
        project_id_str = str(project_id)
        asset_ids_str = [str(aid) for aid in asset_ids]
        
        process_task_id = cls.generate_deterministic_task_id("process", project_id_str, asset_ids_str)
        index_task_id = cls.generate_deterministic_task_id("index", project_id_str, asset_ids_str)

        index_meta = celery_app.backend.get_task_meta(index_task_id)

        print(index_meta)
        print("=============================================================")
        
        if index_meta:
            if index_meta.get('status') == 'SUCCESS':
                return {"status": "ALREADY_DONE", "message": "Assets already processed and indexed."}
            elif index_meta.get('status') in ['RETRY', 'STARTED']:
                return {"status": "IN_PROGRESS", "message": "Assets are currently being indexed."}

        process_meta = celery_app.backend.get_task_meta(process_task_id)

        print(process_meta)
        print("sssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss")

        if process_meta:
            if process_meta.get('status') == 'SUCCESS':
                # المعالجة تمت.. نقوم بتشغيل الفهرسة كـ مهمة مستقلة باستخدام .si() 
                index_task = index_assets_task.si(project_id_str, asset_ids_str).set(task_id=index_task_id)
                index_task.apply_async()
                
                return {"status": "RESUMED_INDEXING", "message": "Resumed indexing for already processed assets."}
            
            elif process_meta.get('status') in ['RETRY', 'STARTED']:
                return {"status": "IN_PROGRESS", "message": "Assets are currently being processed."}

        workflow = chain(
            process_assets_task.si(project_id_str, asset_ids_str, chunk_size, chunk_overlap).set(task_id=process_task_id),
            index_assets_task.si(project_id_str, asset_ids_str).set(task_id=index_task_id) 
        )
        
        workflow.apply_async()
        return {"status": "STARTED", "message": "Started processing and indexing workflow."}


    @classmethod
    def trigger_index_only(cls, project_id: UUID, asset_ids: list[UUID]):
        """استدعاء مهمة الفهرسة بشكل منفصل كلياً (يُستخدم مع Endpoint الفهرسة)"""
        project_id_str = str(project_id)
        asset_ids_str = [str(aid) for aid in asset_ids]
        
        index_task_id = cls.generate_deterministic_task_id("index", project_id_str, asset_ids_str)

        index_meta = celery_app.backend.get_task_meta(index_task_id)
        if index_meta:
            status = index_meta.get('status')
            if status == 'SUCCESS':
                return {"status": "ALREADY_DONE", "message": "Assets already indexed successfully."}
            elif status in ['PENDING', 'STARTED', 'RETRY']:
                return {"status": "IN_PROGRESS", "message": "Assets are currently being indexed."}

        index_task = index_assets_task.si(project_id_str, asset_ids_str).set(task_id=index_task_id)
        index_task.apply_async()
        
        return {
            "status": "STARTED", 
            "message": "Started indexing workflow.", 
            "index_task_id": index_task_id
        }
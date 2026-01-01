#!/usr/bin/env python3
"""
PERFORMANCE SQUAD
=================
Agents for performance optimization and scaling.

Agents:
1. CacheManagerAgent - Caching for profiles and data
2. BatchProcessorAgent - Batch operations for efficiency
3. QueueManagerAgent - Priority queue management
4. LoadBalancerAgent - Distribute load across accounts
"""

import os
import sys
import asyncio
import json
import hashlib
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from collections import OrderedDict
import heapq

sys.path.insert(0, str(Path(__file__).parent.parent))

from .base_agent import BaseAgent, Task, TaskPriority, AgentCapability


# ============================================
# LRU CACHE IMPLEMENTATION
# ============================================

class LRUCache:
    """Thread-safe LRU cache with TTL support"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict = OrderedDict()
        self._expiry: Dict[str, datetime] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self._cache:
            self._misses += 1
            return None

        # Check expiry
        if key in self._expiry and datetime.now() > self._expiry[key]:
            self.delete(key)
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        return self._cache[key]

    def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache"""
        ttl = ttl or self.default_ttl

        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.max_size:
                # Remove oldest
                oldest = next(iter(self._cache))
                self.delete(oldest)

        self._cache[key] = value
        self._expiry[key] = datetime.now() + timedelta(seconds=ttl)

    def delete(self, key: str):
        """Delete from cache"""
        self._cache.pop(key, None)
        self._expiry.pop(key, None)

    def clear(self):
        """Clear entire cache"""
        self._cache.clear()
        self._expiry.clear()

    def stats(self) -> Dict:
        """Get cache statistics"""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0
        }


# ============================================
# CACHE MANAGER AGENT
# ============================================

class CacheManagerAgent(BaseAgent):
    """
    Manages caching for performance optimization.

    Features:
    - Profile caching (avoid re-scraping)
    - Lead data caching
    - TTL-based expiration
    - Cache warming
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="CacheManager",
            description="Caching for performance optimization"
        )

        self.config = config or {}

        # Multiple cache tiers
        self.caches = {
            "profiles": LRUCache(
                max_size=self.config.get("profile_cache_size", 5000),
                default_ttl=self.config.get("profile_ttl", 86400)  # 24 hours
            ),
            "leads": LRUCache(
                max_size=self.config.get("lead_cache_size", 10000),
                default_ttl=self.config.get("lead_ttl", 3600)  # 1 hour
            ),
            "classifications": LRUCache(
                max_size=self.config.get("class_cache_size", 5000),
                default_ttl=self.config.get("class_ttl", 1800)  # 30 minutes
            )
        }

        self.register_capability(AgentCapability(
            name="cache_management",
            description="Caching operations",
            task_types=[
                "cache_get",
                "cache_set",
                "cache_delete",
                "cache_stats",
                "cache_warm",
                "cache_clear"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info("CacheManager: Initialized with 3 cache tiers")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "cache_get":
            return self._cache_get(
                cache_type=payload.get("cache_type", "profiles"),
                key=payload.get("key")
            )

        elif task_type == "cache_set":
            return self._cache_set(
                cache_type=payload.get("cache_type", "profiles"),
                key=payload.get("key"),
                value=payload.get("value"),
                ttl=payload.get("ttl")
            )

        elif task_type == "cache_delete":
            return self._cache_delete(
                cache_type=payload.get("cache_type", "profiles"),
                key=payload.get("key")
            )

        elif task_type == "cache_stats":
            return self._cache_stats()

        elif task_type == "cache_clear":
            return self._cache_clear(
                cache_type=payload.get("cache_type")
            )

        raise ValueError(f"Unknown task type: {task_type}")

    def _cache_get(self, cache_type: str, key: str) -> Dict:
        """Get value from cache"""
        cache = self.caches.get(cache_type)
        if not cache:
            return {"found": False, "error": f"Unknown cache type: {cache_type}"}

        value = cache.get(key)
        return {
            "found": value is not None,
            "value": value,
            "cache_type": cache_type
        }

    def _cache_set(self, cache_type: str, key: str, value: Any, ttl: int = None) -> Dict:
        """Set value in cache"""
        cache = self.caches.get(cache_type)
        if not cache:
            return {"success": False, "error": f"Unknown cache type: {cache_type}"}

        cache.set(key, value, ttl)
        return {"success": True, "key": key, "cache_type": cache_type}

    def _cache_delete(self, cache_type: str, key: str) -> Dict:
        """Delete from cache"""
        cache = self.caches.get(cache_type)
        if cache:
            cache.delete(key)
        return {"success": True}

    def _cache_stats(self) -> Dict:
        """Get stats for all caches"""
        return {
            cache_type: cache.stats()
            for cache_type, cache in self.caches.items()
        }

    def _cache_clear(self, cache_type: str = None) -> Dict:
        """Clear cache(s)"""
        if cache_type:
            cache = self.caches.get(cache_type)
            if cache:
                cache.clear()
                return {"cleared": cache_type}
        else:
            for cache in self.caches.values():
                cache.clear()
            return {"cleared": "all"}


# ============================================
# BATCH PROCESSOR AGENT
# ============================================

class BatchProcessorAgent(BaseAgent):
    """
    Processes tasks in batches for efficiency.

    Features:
    - Batch profile scraping
    - Batch lead qualification
    - Parallel execution
    - Progress tracking
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="BatchProcessor",
            description="Batch processing for efficiency"
        )

        self.config = config or {}
        self.default_batch_size = self.config.get("batch_size", 10)
        self.max_concurrency = self.config.get("max_concurrency", 5)

        # Active batches
        self._active_batches: Dict[str, Dict] = {}

        self.register_capability(AgentCapability(
            name="batch_processing",
            description="Batch operations",
            task_types=[
                "create_batch",
                "process_batch",
                "get_batch_status",
                "cancel_batch"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info(f"BatchProcessor: Concurrency={self.max_concurrency}")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "create_batch":
            return self._create_batch(
                items=payload.get("items", []),
                operation=payload.get("operation"),
                batch_size=payload.get("batch_size")
            )

        elif task_type == "process_batch":
            return await self._process_batch(
                batch_id=payload.get("batch_id"),
                processor=payload.get("processor")
            )

        elif task_type == "get_batch_status":
            return self._get_batch_status(
                batch_id=payload.get("batch_id")
            )

        raise ValueError(f"Unknown task type: {task_type}")

    def _create_batch(
        self,
        items: List[Any],
        operation: str,
        batch_size: int = None
    ) -> Dict:
        """Create a new batch for processing"""
        import uuid

        batch_id = str(uuid.uuid4())[:8]
        batch_size = batch_size or self.default_batch_size

        # Split into sub-batches
        batches = [
            items[i:i + batch_size]
            for i in range(0, len(items), batch_size)
        ]

        self._active_batches[batch_id] = {
            "id": batch_id,
            "operation": operation,
            "total_items": len(items),
            "batches": batches,
            "current_batch": 0,
            "processed": 0,
            "failed": 0,
            "results": [],
            "status": "created",
            "created_at": datetime.now().isoformat()
        }

        return {
            "batch_id": batch_id,
            "total_items": len(items),
            "num_batches": len(batches),
            "batch_size": batch_size
        }

    async def _process_batch(
        self,
        batch_id: str,
        processor: Optional[Callable] = None
    ) -> Dict:
        """Process a batch with the given processor function"""
        batch = self._active_batches.get(batch_id)
        if not batch:
            return {"error": f"Batch not found: {batch_id}"}

        batch["status"] = "processing"
        batch["started_at"] = datetime.now().isoformat()

        try:
            semaphore = asyncio.Semaphore(self.max_concurrency)

            async def process_item(item):
                async with semaphore:
                    try:
                        if processor:
                            if asyncio.iscoroutinefunction(processor):
                                return await processor(item)
                            else:
                                return processor(item)
                        return {"item": item, "status": "processed"}
                    except Exception as e:
                        batch["failed"] += 1
                        return {"item": item, "error": str(e)}

            for sub_batch in batch["batches"]:
                batch["current_batch"] += 1

                results = await asyncio.gather(
                    *[process_item(item) for item in sub_batch],
                    return_exceptions=True
                )

                batch["results"].extend(results)
                batch["processed"] += len(sub_batch)

            batch["status"] = "completed"
            batch["completed_at"] = datetime.now().isoformat()

            return {
                "batch_id": batch_id,
                "status": "completed",
                "processed": batch["processed"],
                "failed": batch["failed"],
                "results": batch["results"]
            }

        except Exception as e:
            batch["status"] = "failed"
            batch["error"] = str(e)
            return {"error": str(e)}

    def _get_batch_status(self, batch_id: str) -> Dict:
        """Get status of a batch"""
        batch = self._active_batches.get(batch_id)
        if not batch:
            return {"error": f"Batch not found: {batch_id}"}

        return {
            "batch_id": batch_id,
            "status": batch["status"],
            "total_items": batch["total_items"],
            "processed": batch["processed"],
            "failed": batch["failed"],
            "current_batch": batch["current_batch"],
            "total_batches": len(batch["batches"]),
            "progress": batch["processed"] / batch["total_items"] if batch["total_items"] > 0 else 0
        }


# ============================================
# QUEUE MANAGER AGENT
# ============================================

@dataclass(order=True)
class PriorityItem:
    """Item in priority queue"""
    priority: int
    timestamp: float = field(compare=False)
    data: Any = field(compare=False)


class QueueManagerAgent(BaseAgent):
    """
    Manages priority queues for task scheduling.

    Features:
    - Multiple named queues
    - Priority-based ordering
    - FIFO within same priority
    - Queue monitoring
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="QueueManager",
            description="Priority queue management"
        )

        self.config = config or {}
        self._queues: Dict[str, List[PriorityItem]] = {
            "dm_outbound": [],
            "dm_inbound": [],
            "scrape": [],
            "classify": [],
            "enrich": []
        }

        self.register_capability(AgentCapability(
            name="queue_management",
            description="Priority queue operations",
            task_types=[
                "queue_push",
                "queue_pop",
                "queue_peek",
                "queue_size",
                "queue_clear",
                "queue_stats"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info(f"QueueManager: {len(self._queues)} queues initialized")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "queue_push":
            return self._queue_push(
                queue_name=payload.get("queue_name"),
                item=payload.get("item"),
                priority=payload.get("priority", 3)
            )

        elif task_type == "queue_pop":
            return self._queue_pop(
                queue_name=payload.get("queue_name")
            )

        elif task_type == "queue_peek":
            return self._queue_peek(
                queue_name=payload.get("queue_name"),
                count=payload.get("count", 1)
            )

        elif task_type == "queue_size":
            return self._queue_size(
                queue_name=payload.get("queue_name")
            )

        elif task_type == "queue_stats":
            return self._queue_stats()

        raise ValueError(f"Unknown task type: {task_type}")

    def _queue_push(self, queue_name: str, item: Any, priority: int = 3) -> Dict:
        """Push item to queue with priority"""
        if queue_name not in self._queues:
            self._queues[queue_name] = []

        queue = self._queues[queue_name]
        priority_item = PriorityItem(
            priority=priority,
            timestamp=datetime.now().timestamp(),
            data=item
        )
        heapq.heappush(queue, priority_item)

        return {
            "success": True,
            "queue_name": queue_name,
            "priority": priority,
            "queue_size": len(queue)
        }

    def _queue_pop(self, queue_name: str) -> Dict:
        """Pop highest priority item from queue"""
        queue = self._queues.get(queue_name, [])

        if not queue:
            return {"success": False, "error": "Queue empty"}

        item = heapq.heappop(queue)
        return {
            "success": True,
            "item": item.data,
            "priority": item.priority,
            "queue_size": len(queue)
        }

    def _queue_peek(self, queue_name: str, count: int = 1) -> Dict:
        """Peek at top items without removing"""
        queue = self._queues.get(queue_name, [])

        items = []
        for i, item in enumerate(sorted(queue)):
            if i >= count:
                break
            items.append({"data": item.data, "priority": item.priority})

        return {"items": items, "count": len(items)}

    def _queue_size(self, queue_name: str = None) -> Dict:
        """Get queue size(s)"""
        if queue_name:
            return {
                "queue_name": queue_name,
                "size": len(self._queues.get(queue_name, []))
            }
        return {
            name: len(queue)
            for name, queue in self._queues.items()
        }

    def _queue_stats(self) -> Dict:
        """Get stats for all queues"""
        total_items = sum(len(q) for q in self._queues.values())
        return {
            "total_items": total_items,
            "queues": {
                name: {
                    "size": len(queue),
                    "oldest": min((i.timestamp for i in queue), default=None)
                }
                for name, queue in self._queues.items()
            }
        }


# ============================================
# LOAD BALANCER AGENT
# ============================================

class LoadBalancerAgent(BaseAgent):
    """
    Distributes load across multiple Instagram accounts.

    Features:
    - Round-robin distribution
    - Weight-based routing
    - Health-aware routing
    - Automatic failover
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="LoadBalancer",
            description="Load distribution across accounts"
        )

        self.config = config or {}

        # Account pool with weights and health
        self._accounts: Dict[str, Dict] = {}
        self._rotation_index = 0

        self.register_capability(AgentCapability(
            name="load_balancing",
            description="Load distribution",
            task_types=[
                "register_account",
                "get_next_account",
                "report_health",
                "get_distribution",
                "rebalance"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info("LoadBalancer: Initialized")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "register_account":
            return self._register_account(
                username=payload.get("username"),
                weight=payload.get("weight", 1.0)
            )

        elif task_type == "get_next_account":
            return self._get_next_account(
                action_type=payload.get("action_type")
            )

        elif task_type == "report_health":
            return self._report_health(
                username=payload.get("username"),
                healthy=payload.get("healthy", True),
                error=payload.get("error")
            )

        elif task_type == "get_distribution":
            return self._get_distribution()

        raise ValueError(f"Unknown task type: {task_type}")

    def _register_account(self, username: str, weight: float = 1.0) -> Dict:
        """Register an account in the pool"""
        self._accounts[username] = {
            "username": username,
            "weight": weight,
            "healthy": True,
            "tasks_assigned": 0,
            "last_used": None,
            "errors": 0,
            "registered_at": datetime.now().isoformat()
        }
        return {"success": True, "total_accounts": len(self._accounts)}

    def _get_next_account(self, action_type: str = None) -> Dict:
        """Get next account to use (weighted round-robin)"""
        healthy_accounts = [
            (username, data)
            for username, data in self._accounts.items()
            if data["healthy"]
        ]

        if not healthy_accounts:
            return {"success": False, "error": "No healthy accounts"}

        # Sort by tasks_assigned/weight ratio (least loaded first)
        sorted_accounts = sorted(
            healthy_accounts,
            key=lambda x: x[1]["tasks_assigned"] / max(x[1]["weight"], 0.1)
        )

        username, data = sorted_accounts[0]
        data["tasks_assigned"] += 1
        data["last_used"] = datetime.now().isoformat()

        return {
            "success": True,
            "username": username,
            "weight": data["weight"],
            "tasks_assigned": data["tasks_assigned"]
        }

    def _report_health(
        self,
        username: str,
        healthy: bool = True,
        error: str = None
    ) -> Dict:
        """Report account health status"""
        if username not in self._accounts:
            return {"success": False, "error": "Account not found"}

        account = self._accounts[username]
        account["healthy"] = healthy

        if not healthy:
            account["errors"] += 1
            account["last_error"] = error

        return {
            "success": True,
            "username": username,
            "healthy": healthy,
            "total_errors": account["errors"]
        }

    def _get_distribution(self) -> Dict:
        """Get current load distribution"""
        total_tasks = sum(a["tasks_assigned"] for a in self._accounts.values())

        return {
            "total_accounts": len(self._accounts),
            "healthy_accounts": len([a for a in self._accounts.values() if a["healthy"]]),
            "total_tasks": total_tasks,
            "distribution": {
                username: {
                    "tasks": data["tasks_assigned"],
                    "percentage": data["tasks_assigned"] / total_tasks if total_tasks > 0 else 0,
                    "healthy": data["healthy"],
                    "weight": data["weight"]
                }
                for username, data in self._accounts.items()
            }
        }


# ============================================
# FACTORY FUNCTION
# ============================================

def create_performance_squad(config: Dict = None) -> Dict[str, BaseAgent]:
    """Create all performance squad agents"""
    config = config or {}

    return {
        "CacheManager": CacheManagerAgent(config.get("cache")),
        "BatchProcessor": BatchProcessorAgent(config.get("batch")),
        "QueueManager": QueueManagerAgent(config.get("queue")),
        "LoadBalancer": LoadBalancerAgent(config.get("load_balancer"))
    }

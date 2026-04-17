"""
services/report_service.py — Tổng hợp dữ liệu cho Dashboard/Reports
Dùng MongoDB aggregation pipeline — tránh N+1 query.

Methods:
    get_revenue()        → RevenueReport (doanh thu theo ngày / loại vé)
    get_visitors()       → VisitorReport (lượt vào/ra, peak hours, channel usage)
    get_error_rates()    → ErrorRateReport (tỷ lệ lỗi theo kênh)
    get_realtime_stats() → RealtimeStats  (snapshot cho WebSocket, mỗi 5 giây)
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class ReportService:

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db

    # ── Revenue ───────────────────────────────────────────────

    async def get_revenue(
        self,
        date_from: datetime,
        date_to:   datetime,
    ) -> dict:
        """
        Doanh thu theo ngày và loại vé.
        Dùng cho RevenueLineChart và bảng tổng hợp.

        Tối ưu: transactions đã lưu ticket_type sẵn (không cần $lookup).
        """
        match = {"created_at": {"$gte": date_from, "$lte": date_to}}

        # Tổng doanh thu + số vé
        total_pipe = [
            {"$match": match},
            {"$group": {
                "_id":   None,
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }},
        ]
        total_rows    = await self._db["transactions"].aggregate(total_pipe).to_list(1)
        total_revenue = total_rows[0]["total"] if total_rows else 0.0
        total_tickets = total_rows[0]["count"] if total_rows else 0

        # Doanh thu theo loại vé — dùng ticket_type đã copy vào transactions
        by_type_pipe = [
            {"$match": match},
            {"$group": {
                "_id":     "$ticket_type",
                "revenue": {"$sum": "$amount"},
                "count":   {"$sum": 1},
            }},
            {"$sort": {"revenue": -1}},
        ]
        by_type_rows = await self._db["transactions"].aggregate(by_type_pipe).to_list(10)
        by_type = {
            (r["_id"] or "unknown"): {"revenue": r["revenue"], "count": r["count"]}
            for r in by_type_rows
        }

        # Doanh thu theo ngày
        by_date_pipe = [
            {"$match": match},
            {"$group": {
                "_id":     {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "revenue": {"$sum": "$amount"},
                "count":   {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]
        by_date_rows = await self._db["transactions"].aggregate(by_date_pipe).to_list(366)
        by_date = [
            {"date": r["_id"], "revenue": r["revenue"], "count": r["count"]}
            for r in by_date_rows
        ]

        return {
            "total_revenue": total_revenue,
            "total_tickets": total_tickets,
            "by_type":       by_type,
            "by_date":       by_date,
        }

    # ── Visitors ─────────────────────────────────────────────

    async def get_visitors(
        self,
        date_from: datetime,
        date_to:   datetime,
        gate_id:   Optional[str] = None,
    ) -> dict:
        """
        Thống kê lượt vào/ra theo cổng, giờ, kênh.
        Dùng cho ChannelPieChart, PeakHourChart, GateStatusCard.
        """
        match: dict = {
            "created_at": {"$gte": date_from, "$lte": date_to},
            "result":     "SUCCESS",
        }
        if gate_id:
            match["gate_id"] = gate_id

        # Tổng IN / OUT
        dir_pipe = [
            {"$match": match},
            {"$group": {"_id": "$direction", "count": {"$sum": 1}}},
        ]
        dir_rows       = await self._db["gate_events"].aggregate(dir_pipe).to_list(5)
        dir_map        = {r["_id"]: r["count"] for r in dir_rows}
        total_checkins  = dir_map.get("IN",  0)
        total_checkouts = dir_map.get("OUT", 0)

        # Khách hiện tại trong khu = IN - OUT của hôm nay
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_match = {**match, "created_at": {"$gte": today_start}}
        today_pipe  = [
            {"$match": today_match},
            {"$group": {"_id": "$direction", "count": {"$sum": 1}}},
        ]
        today_rows     = await self._db["gate_events"].aggregate(today_pipe).to_list(5)
        today_map      = {r["_id"]: r["count"] for r in today_rows}
        current_inside = max(0, today_map.get("IN", 0) - today_map.get("OUT", 0))

        # Theo cổng — join gate name
        by_gate_pipe = [
            {"$match": match},
            {"$group": {"_id": "$gate_id", "count": {"$sum": 1}}},
            {"$lookup": {
                "from":         "gates",
                "localField":   "_id",
                "foreignField": "_id",
                "as":           "gate",
            }},
            {"$unwind": {"path": "$gate", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "gate_id": "$_id",
                "gate":    {"$ifNull": ["$gate.name", "?"]},
                "count":   1,
            }},
            {"$sort": {"count": -1}},
        ]
        by_gate = await self._db["gate_events"].aggregate(by_gate_pipe).to_list(20)
        for g in by_gate:
            g.pop("_id", None)

        # Peak hours (0–23)
        by_hour_pipe = [
            {"$match": match},
            {"$group": {
                "_id":   {"$hour": "$created_at"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]
        by_hour_rows = await self._db["gate_events"].aggregate(by_hour_pipe).to_list(24)
        by_hour = [{"hour": r["_id"], "count": r["count"]} for r in by_hour_rows]

        # Theo kênh xác thực
        by_channel_pipe = [
            {"$match": match},
            {"$group": {"_id": "$channel", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        by_channel_rows = await self._db["gate_events"].aggregate(by_channel_pipe).to_list(10)
        by_channel = [{"channel": r["_id"], "count": r["count"]} for r in by_channel_rows]

        return {
            "total_checkins":  total_checkins,
            "total_checkouts": total_checkouts,
            "current_inside":  current_inside,
            "by_gate":         by_gate,
            "by_hour":         by_hour,
            "by_channel":      by_channel,
        }

    # ── Error rates ───────────────────────────────────────────

    async def get_error_rates(
        self,
        date_from: datetime,
        date_to:   datetime,
    ) -> dict:
        """
        Tỷ lệ lỗi check-in/out theo từng kênh.
        Dùng cho biểu đồ ErrorRateChart.
        """
        match = {"created_at": {"$gte": date_from, "$lte": date_to}}

        pipeline = [
            {"$match": match},
            {"$group": {
                "_id":    "$channel",
                "total":  {"$sum": 1},
                "failed": {"$sum": {"$cond": [{"$eq": ["$result", "FAIL"]}, 1, 0]}},
            }},
            {"$addFields": {
                "error_rate": {
                    "$cond": [
                        {"$gt": ["$total", 0]},
                        {"$multiply": [{"$divide": ["$failed", "$total"]}, 100]},
                        0,
                    ]
                }
            }},
            {"$sort": {"total": -1}},
        ]
        rows = await self._db["gate_events"].aggregate(pipeline).to_list(10)

        total_all  = sum(r["total"]  for r in rows)
        failed_all = sum(r["failed"] for r in rows)

        return {
            "date_from":          date_from.isoformat(),
            "date_to":            date_to.isoformat(),
            "total_events":       total_all,
            "total_failed":       failed_all,
            "overall_error_rate": round(failed_all / total_all * 100, 2) if total_all > 0 else 0.0,
            "by_channel": [
                {
                    "channel":    r["_id"],
                    "total":      r["total"],
                    "failed":     r["failed"],
                    "error_rate": round(r.get("error_rate", 0), 2),
                }
                for r in rows
            ],
        }

    # ── Realtime stats ────────────────────────────────────────

    async def get_realtime_stats(self) -> dict:
        """
        Snapshot realtime — gửi qua WebSocket mỗi 5 giây.
        Cũng dùng cho GET /api/reports/realtime (poll fallback).

        Tối ưu: gates_status dùng aggregation thay vì N+1 query.
        """
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        match_today         = {"created_at":  {"$gte": today_start}}
        match_success_today = {**match_today, "result": "SUCCESS"}

        # IN/OUT hôm nay
        dir_pipe  = [
            {"$match": match_success_today},
            {"$group": {"_id": "$direction", "count": {"$sum": 1}}},
        ]
        dir_rows        = await self._db["gate_events"].aggregate(dir_pipe).to_list(5)
        dir_map         = {r["_id"]: r["count"] for r in dir_rows}
        checkins_today  = dir_map.get("IN",  0)
        checkouts_today = dir_map.get("OUT", 0)
        current_inside  = max(0, checkins_today - checkouts_today)

        # Doanh thu hôm nay
        rev_pipe  = [
            {"$match": match_today},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
        rev_rows      = await self._db["transactions"].aggregate(rev_pipe).to_list(1)
        revenue_today = rev_rows[0]["total"] if rev_rows else 0.0

        # Tỷ lệ lỗi hôm nay
        err_pipe = [
            {"$match": match_today},
            {"$group": {
                "_id":    None,
                "total":  {"$sum": 1},
                "failed": {"$sum": {"$cond": [{"$eq": ["$result", "FAIL"]}, 1, 0]}},
            }},
        ]
        err_rows   = await self._db["gate_events"].aggregate(err_pipe).to_list(1)
        total_ev   = err_rows[0]["total"]  if err_rows else 0
        failed_ev  = err_rows[0]["failed"] if err_rows else 0
        error_rate = round(failed_ev / total_ev * 100, 1) if total_ev > 0 else 0.0

        # 10 sự kiện gần nhất
        recent_rows = await self._db["gate_events"].find(
            {},
            {"_id": 1, "ticket_id": 1, "ticket_type": 1,
             "gate_id": 1, "direction": 1, "channel": 1, "result": 1, "created_at": 1},
        ).sort("created_at", -1).limit(10).to_list(10)

        recent_events = []
        for e in recent_rows:
            recent_events.append({
                "event_id":   str(e["_id"]),
                "ticket_id":  e.get("ticket_id"),
                "ticket_type": e.get("ticket_type"),
                "gate_id":    e.get("gate_id"),
                "direction":  e.get("direction"),
                "channel":    e.get("channel"),
                "result":     e.get("result"),
                "created_at": e["created_at"].isoformat() if e.get("created_at") else None,
            })

        # Trạng thái từng cổng — dùng aggregation tránh N+1 query
        # $lookup gate → $group lấy last_event theo gate
        gates_pipe = [
            # Lấy tất cả cổng active
            {"$match": {"is_active": True}},
            # Join event gần nhất của mỗi cổng
            {"$lookup": {
                "from": "gate_events",
                "let":  {"gid": {"$toString": "$_id"}},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$gate_id", "$$gid"]}}},
                    {"$sort":  {"created_at": -1}},
                    {"$limit": 1},
                    {"$project": {"result": 1, "created_at": 1}},
                ],
                "as": "last_events",
            }},
            {"$addFields": {
                "last_event_doc": {"$arrayElemAt": ["$last_events", 0]}
            }},
            {"$project": {
                "gate_code": 1,
                "name":      1,
                "last_result": "$last_event_doc.result",
                "last_time":   "$last_event_doc.created_at",
            }},
        ]
        gates_rows   = await self._db["gates"].aggregate(gates_pipe).to_list(20)
        gates_status = [
            {
                "gate_id":    str(g["_id"]),
                "gate_code":  g.get("gate_code"),
                "name":       g.get("name"),
                "last_event": g.get("last_result"),
                "last_time":  g["last_time"].isoformat() if g.get("last_time") else None,
            }
            for g in gates_rows
        ]

        return {
            "type":            "stats",
            "current_inside":  current_inside,
            "checkins_today":  checkins_today,
            "checkouts_today": checkouts_today,
            "revenue_today":   revenue_today,
            "error_rate_today": error_rate,
            "recent_events":   recent_events,
            "gates_status":    gates_status,
        }
 
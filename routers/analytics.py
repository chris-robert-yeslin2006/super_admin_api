from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta
from database import supabase

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/students")
def get_students_for_analytics(
    org_id: Optional[str] = Query(None),
    language: Optional[str] = Query(None)
):
    """
    Fetch students optionally filtered by organization and language
    """
    query = supabase.table("students").select(
        "id, name, email, language, overall_mark, average_mark, recent_test_mark, "
        "fluency_mark, vocab_mark, sentence_mastery, pronunciation"
    )

    if org_id:
        query = query.eq("org_id", org_id)
    if language:
        query = query.eq("language", language)

    response = query.execute()

    return {"students": response.data}

@router.get("/summary")
def get_summary_for_language(org_id: str = Query(...), language: str = Query(...)):
    """
    Provide summary statistics (like averages) for a given organization and language
    """
    response = supabase.table("students").select(
        "overall_mark, fluency_mark, vocab_mark, pronunciation"
    ).eq("org_id", org_id).eq("language", language).execute()

    data = response.data
    if not data:
        return {"summary": {}}

    # Compute averages
    total = len(data)
    summary = {
        "avg_overall": sum(s["overall_mark"] for s in data) / total,
        "avg_fluency": sum(s["fluency_mark"] for s in data) / total,
        "avg_vocab": sum(s["vocab_mark"] for s in data) / total,
        "avg_pronunciation": sum(s["pronunciation"] for s in data) / total,
    }

    return {"summary": summary}

@router.get("/language-detail")
def get_language_detail(org_id: str, language: str):
    students = supabase.table("students").select("*")\
        .eq("org_id", org_id).eq("language", language).execute().data

    if not students:
        return {"message": "No data", "total_students": 0}

    average = sum(s["overall_mark"] for s in students) / len(students)
    top_student = max(students, key=lambda s: s["overall_mark"])

    return {
        "language": language,
        "total_students": len(students),
        "average_mark": average,
        "top_student": {
            "name": top_student["name"],
            "overall_mark": top_student["overall_mark"]
        }
    }

@router.get("/organizations/status")
def get_organizations_by_status(
    timeframe: str = Query("7days", description="Time period: 7days, 15days, 1month, quarter"),
    start_date: Optional[str] = Query(None, description="Optional custom start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Optional custom end date (YYYY-MM-DD)")
):
    """
    Get organization counts grouped by status for the specified timeframe.
    """
    # Calculate date range based on timeframe or custom dates
    today = datetime.now()
    
    if start_date and end_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        # Set date range based on timeframe parameter
        if timeframe == "7days":
            start = today - timedelta(days=7)
        elif timeframe == "15days":
            start = today - timedelta(days=15)
        elif timeframe == "1month":
            start = today - timedelta(days=30)
        elif timeframe == "quarter":
            start = today - timedelta(days=90)
        else:
            start = today - timedelta(days=7)  # Default to 7 days
        end = today
    
    # Convert to string format that Supabase expects
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    
    # Query organizations created within the date range
    query = supabase.table("organizations") \
        .select("id, name, status, created_at") \
        .gte("created_at", start_str) \
        .lte("created_at", end_str + "T23:59:59")
    
    response = query.execute()
    
    if not response.data:
        return {"data": [], "timeframe": timeframe}
    
    # Format response data for the chart
    result = {
        "data": response.data,
        "timeframe": timeframe,
        "date_range": {
            "start": start_str,
            "end": end_str
        }
    }
    
    return result

@router.get("/organizations/timeline")
def get_organizations_timeline(
    timeframe: str = Query("7days", description="Time period: 7days, 15days, 1month, quarter, halfyear, year")
):
    """
    Get organization counts over time, formatted for timeline charts.
    """
    # Map DB status to chart keys
    status_key_map = {
        "onboard": "onboarded",
        "contacted": "contacted",
        "standby": "standby",
        "under verification": "verification"
    }

    today = datetime.now()
    
    if timeframe == "7days":
        start_date = today - timedelta(days=7)
        group_by = "day"
    elif timeframe == "15days":
        start_date = today - timedelta(days=15)
        group_by = "day"
    elif timeframe == "1month":
        start_date = today - timedelta(days=30)
        group_by = "week"
    elif timeframe == "quarter":
        start_date = today - timedelta(days=90)
        group_by = "month"
    elif timeframe == "halfyear":
        start_date = today - timedelta(days=180)
        group_by = "month"
    elif timeframe == "year":
        start_date = today - timedelta(days=365)
        group_by = "month"
    else:
        start_date = today - timedelta(days=7)
        group_by = "day"

    start_str = start_date.strftime("%Y-%m-%d")

    response = supabase.table("organizations") \
        .select("id, name, status, created_at") \
        .gte("created_at", start_str) \
        .order("created_at") \
        .execute()
    
    organizations = response.data
    result = []

    if group_by == "day":
        date_format = "%Y-%m-%d"
        date_label_format = "%b %d"

        date_counts = {}
        current_date = start_date
        while current_date <= today:
            date_str = current_date.strftime(date_format)
            date_counts[date_str] = {
                "date": date_str,
                "label": current_date.strftime(date_label_format),
                "onboarded": 0,
                "contacted": 0,
                "standby": 0,
                "verification": 0
            }
            current_date += timedelta(days=1)

        for org in organizations:
            org_date = datetime.fromisoformat(org["created_at"].replace("Z", "+00:00")).strftime(date_format)
            status = org.get("status", "onboard")
            mapped_status = status_key_map.get(status)

            if mapped_status and mapped_status in date_counts[org_date]:
                date_counts[org_date][mapped_status] += 1

        result = list(date_counts.values())

    elif group_by == "week":
        weeks = []
        week_start = start_date
        while week_start <= today:
            week_end = week_start + timedelta(days=6)
            if week_end > today:
                week_end = today
            week_label = f"Week {len(weeks) + 1}"
            weeks.append({
                "start": week_start,
                "end": week_end,
                "label": week_label,
                "onboarded": 0,
                "contacted": 0,
                "standby": 0,
                "verification": 0
            })
            week_start = week_end + timedelta(days=1)

        for org in organizations:
            org_date = datetime.fromisoformat(org["created_at"].replace("Z", "+00:00"))
            status = org.get("status", "onboard")
            mapped_status = status_key_map.get(status)

            for week in weeks:
                if week["start"] <= org_date <= week["end"]:
                    if mapped_status and mapped_status in week:
                        week[mapped_status] += 1
                    break

        result = [
            {
                "name": week["label"],
                "onboarded": week["onboarded"],
                "contacted": week["contacted"],
                "standby": week["standby"],
                "verification": week["verification"]
            }
            for week in weeks
        ]

    elif group_by == "month":
        months = []
        current_month = datetime(start_date.year, start_date.month, 1)

        while current_month <= today:
            next_month = datetime(
                current_month.year + (1 if current_month.month == 12 else 0),
                1 if current_month.month == 12 else current_month.month + 1,
                1
            )
            month_label = current_month.strftime("%b")
            months.append({
                "start": current_month,
                "end": next_month - timedelta(days=1),
                "label": month_label,
                "onboarded": 0,
                "contacted": 0,
                "standby": 0,
                "verification": 0
            })
            current_month = next_month

        for org in organizations:
            org_date = datetime.fromisoformat(org["created_at"].replace("Z", "+00:00"))
            status = org.get("status", "onboard")
            mapped_status = status_key_map.get(status)

            for month in months:
                if month["start"] <= org_date <= month["end"]:
                    if mapped_status and mapped_status in month:
                        month[mapped_status] += 1
                    break

        result = [
            {
                "name": month["label"],
                "onboarded": month["onboarded"],
                "contacted": month["contacted"],
                "standby": month["standby"],
                "verification": month["verification"]
            }
            for month in months
        ]

    return {
        "data": result,
        "timeframe": timeframe,
        "group_by": group_by
    }

@router.get("/students/timeline")
def get_students_timeline(
    timeframe: str = Query("7days", description="Time period: 7days, 15days, 1month, quarter"),
    language: Optional[str] = Query(None, description="Filter by language"),
    org_id: Optional[str] = Query(None, description="Filter by organization ID")
):
    """
    Get student counts over time, formatted for timeline charts.
    """
    # Calculate start date based on timeframe
    today = datetime.now()
    
    if timeframe == "7days":
        start_date = today - timedelta(days=7)
    elif timeframe == "15days":
        start_date = today - timedelta(days=15)
    elif timeframe == "1month":
        start_date = today - timedelta(days=30)
    elif timeframe == "quarter":
        start_date = today - timedelta(days=90)
    else:
        start_date = today - timedelta(days=7)
    
    # Format start date for Supabase query
    start_str = start_date.strftime("%Y-%m-%d")
    
    # Build the query
    query = supabase.table("students").select("id, name, language, created_at, org_id").gte("created_at", start_str)
    
    # Add filters if provided
    if language:
        query = query.eq("language", language)
    if org_id:
        query = query.eq("org_id", org_id)
    
    response = query.execute()
    students = response.data
    
    # Format data by day
    date_format = "%Y-%m-%d"
    date_label_format = "%b %d"  # e.g., "Jan 01"
    
    # Create a dictionary to store counts by date
    date_counts = {}
    
    # Initialize all dates in the range
    current_date = start_date
    while current_date <= today:
        date_str = current_date.strftime(date_format)
        date_counts[date_str] = {
            "date": date_str,
            "label": current_date.strftime(date_label_format),
            "count": 0
        }
        current_date += timedelta(days=1)
    
    # Count students by date
    for student in students:
        student_date = datetime.fromisoformat(student["created_at"].replace("Z", "+00:00")).strftime(date_format)
        if student_date in date_counts:
            date_counts[student_date]["count"] += 1
    
    # Convert to list for the response
    result = list(date_counts.values())
    
    return {
        "data": result,
        "timeframe": timeframe,
        "filters": {
            "language": language,
            "org_id": org_id
        }
    }
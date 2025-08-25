# app/health_analytics.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
import logging
from datetime import datetime, timedelta
import json

from .database import get_session
from .models import AnalysisHistory, User, Appointment
from .schemas import HealthSummary, AnalyticsData
from .utils import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health & Analytics"])

# Auth scheme
oauth2_scheme = HTTPBearer()

# Dependency to get current user from JWT
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = credentials.credentials
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    
    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token: invalid user ID format")

@router.get("/summary", response_model=HealthSummary)
def get_health_summary(
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get user's health summary"""
    try:
        # Get total analyses
        total_analyses = session.exec(
            select(func.count(AnalysisHistory.id))
            .where(AnalysisHistory.user_id == current_user)
        ).first() or 0
        
        # Get last analysis date
        last_analysis = session.exec(
            select(AnalysisHistory)
            .where(AnalysisHistory.user_id == current_user)
            .order_by(AnalysisHistory.created_at.desc())
        ).first()
        
        last_analysis_date = None
        if last_analysis:
            last_analysis_date = last_analysis.created_at.strftime("%Y-%m-%d")
        
        # Calculate health score (simplified - you can implement more sophisticated scoring)
        health_score = 0
        if total_analyses > 0:
            # Basic scoring based on number of analyses and recency
            base_score = min(total_analyses * 10, 50)  # Max 50 points for regular checkups
            
            # Add points for recent analysis
            if last_analysis:
                days_since_last = (datetime.utcnow() - last_analysis.created_at).days
                if days_since_last <= 30:
                    recency_score = 30
                elif days_since_last <= 90:
                    recency_score = 20
                elif days_since_last <= 180:
                    recency_score = 10
                else:
                    recency_score = 0
                
                health_score = min(base_score + recency_score, 100)
        
        # Generate recommendations
        recommendations = []
        if total_analyses == 0:
            recommendations.append("Schedule your first dental checkup")
        elif last_analysis:
            days_since_last = (datetime.utcnow() - last_analysis.created_at).days
            if days_since_last > 180:
                recommendations.append("Schedule a dental checkup - it's been over 6 months")
            elif days_since_last > 90:
                recommendations.append("Consider scheduling a follow-up appointment")
        
        recommendations.extend([
            "Brush your teeth twice daily",
            "Floss regularly",
            "Limit sugary foods and drinks",
            "Visit your dentist for regular checkups"
        ])
        
        # Calculate next checkup date
        next_checkup_date = None
        if last_analysis:
            next_checkup_date = (last_analysis.created_at + timedelta(days=180)).strftime("%Y-%m-%d")
        
        logger.info(f"Generated health summary for user {current_user}")
        
        return HealthSummary(
            total_analyses=total_analyses,
            last_analysis_date=last_analysis_date,
            health_score=health_score,
            recommendations=recommendations,
            next_checkup_date=next_checkup_date
        )
        
    except Exception as e:
        logger.error(f"Error generating health summary for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate health summary")

@router.get("/analytics")
def get_analytics(
    period: str = Query("month", description="Analytics period: week, month, year"),
    type: str = Query("analyses", description="Analytics type: analyses, appointments, health_score"),
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get analytics data for the user"""
    try:
        # Validate period
        if period not in ["week", "month", "year"]:
            raise HTTPException(status_code=400, detail="Invalid period. Must be week, month, or year")
        
        # Validate type
        if type not in ["analyses", "appointments", "health_score"]:
            raise HTTPException(status_code=400, detail="Invalid type. Must be analyses, appointments, or health_score")
        
        # Calculate date range
        end_date = datetime.utcnow()
        if period == "week":
            start_date = end_date - timedelta(days=7)
            group_by = "day"
        elif period == "month":
            start_date = end_date - timedelta(days=30)
            group_by = "day"
        else:  # year
            start_date = end_date - timedelta(days=365)
            group_by = "month"
        
        data = []
        summary = {}
        
        if type == "analyses":
            # Get analysis data
            analyses = session.exec(
                select(AnalysisHistory)
                .where(AnalysisHistory.user_id == current_user)
                .where(AnalysisHistory.created_at >= start_date)
                .where(AnalysisHistory.created_at <= end_date)
                .order_by(AnalysisHistory.created_at)
            ).all()
            
            # Group by date
            analysis_by_date = {}
            for analysis in analyses:
                if group_by == "day":
                    date_key = analysis.created_at.strftime("%Y-%m-%d")
                else:
                    date_key = analysis.created_at.strftime("%Y-%m")
                
                if date_key not in analysis_by_date:
                    analysis_by_date[date_key] = 0
                analysis_by_date[date_key] += 1
            
            # Convert to list format
            for date_key, count in analysis_by_date.items():
                data.append({
                    "date": date_key,
                    "value": count
                })
            
            # Calculate summary
            total_analyses = sum(analysis_by_date.values())
            average_analyses = total_analyses / len(analysis_by_date) if analysis_by_date else 0
            trend = "increasing" if len(data) > 1 and data[-1]["value"] > data[0]["value"] else "stable"
            
            summary = {
                "total": total_analyses,
                "average": round(average_analyses, 2),
                "trend": trend
            }
            
        elif type == "appointments":
            # Get appointment data
            appointments = session.exec(
                select(Appointment)
                .where(Appointment.user_id == current_user)
                .where(Appointment.appointment_date >= start_date.date())
                .where(Appointment.appointment_date <= end_date.date())
                .order_by(Appointment.appointment_date)
            ).all()
            
            # Group by date
            appointment_by_date = {}
            for appointment in appointments:
                if group_by == "day":
                    date_key = appointment.appointment_date.strftime("%Y-%m-%d")
                else:
                    date_key = appointment.appointment_date.strftime("%Y-%m")
                
                if date_key not in appointment_by_date:
                    appointment_by_date[date_key] = 0
                appointment_by_date[date_key] += 1
            
            # Convert to list format
            for date_key, count in appointment_by_date.items():
                data.append({
                    "date": date_key,
                    "value": count
                })
            
            # Calculate summary
            total_appointments = sum(appointment_by_date.values())
            average_appointments = total_appointments / len(appointment_by_date) if appointment_by_date else 0
            trend = "increasing" if len(data) > 1 and data[-1]["value"] > data[0]["value"] else "stable"
            
            summary = {
                "total": total_appointments,
                "average": round(average_appointments, 2),
                "trend": trend
            }
            
        elif type == "health_score":
            # Get health scores over time (simplified)
            analyses = session.exec(
                select(AnalysisHistory)
                .where(AnalysisHistory.user_id == current_user)
                .where(AnalysisHistory.created_at >= start_date)
                .where(AnalysisHistory.created_at <= end_date)
                .order_by(AnalysisHistory.created_at)
            ).all()
            
            # Calculate health score for each analysis (simplified)
            for analysis in analyses:
                if group_by == "day":
                    date_key = analysis.created_at.strftime("%Y-%m-%d")
                else:
                    date_key = analysis.created_at.strftime("%Y-%m")
                
                # Simple health score calculation (you can implement more sophisticated scoring)
                health_score = 75  # Base score, you can analyze the AI report content
                
                data.append({
                    "date": date_key,
                    "value": health_score
                })
            
            # Calculate summary
            if data:
                scores = [item["value"] for item in data]
                total_score = sum(scores)
                average_score = total_score / len(scores)
                trend = "increasing" if len(data) > 1 and data[-1]["value"] > data[0]["value"] else "stable"
                
                summary = {
                    "total": total_score,
                    "average": round(average_score, 2),
                    "trend": trend
                }
            else:
                summary = {
                    "total": 0,
                    "average": 0,
                    "trend": "stable"
                }
        
        logger.info(f"Generated {type} analytics for user {current_user} ({period} period)")
        
        return {
            "success": True,
            "data": {
                "period": period,
                "type": type,
                "data": data,
                "summary": summary
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating analytics for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate analytics")

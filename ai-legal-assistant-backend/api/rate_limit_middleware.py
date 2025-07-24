from fastapi import HTTPException, Depends
from functools import wraps
from services.rate_limiting_service import RateLimitingService
import logging

logger = logging.getLogger(__name__)

rate_limiting_service = RateLimitingService()

async def check_query_rate_limit(current_user):
    """Middleware to check if user can make queries"""
    try:
        can_proceed, info = await rate_limiting_service.check_rate_limit(current_user.id)
        
        if not can_proceed:
            error_type = info.get('error')
            
            if error_type == 'daily_limit_exceeded':
                raise HTTPException(
                    status_code=429,
                    detail={
                        'error': 'DAILY_LIMIT_EXCEEDED',
                        'message': info['message'],
                        'current_usage': info['current_usage'],
                        'daily_limit': info['daily_limit'],
                        'subscription': info['subscription']
                    }
                )
            elif error_type == 'subscription_expired':
                raise HTTPException(
                    status_code=402,
                    detail={
                        'error': 'SUBSCRIPTION_EXPIRED',
                        'message': info['message'],
                        'subscription': info['subscription']
                    }
                )
            elif error_type == 'subscription_inactive':
                raise HTTPException(
                    status_code=403,
                    detail={
                        'error': 'SUBSCRIPTION_INACTIVE',
                        'message': info['message'],
                        'subscription': info['subscription']
                    }
                )
        
        # If we reach here, user can proceed
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rate limiting check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Rate limiting check failed"
        )

async def increment_query_count(current_user):
    """Increment user's daily query count after successful query"""
    try:
        await rate_limiting_service.increment_daily_usage(current_user.id)
    except Exception as e:
        logger.error(f"Failed to increment query count: {str(e)}")
        # Don't fail the request if we can't increment the counter
        pass
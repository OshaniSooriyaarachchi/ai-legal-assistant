from datetime import date, datetime
from typing import Dict, Optional, Tuple
from config.supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)

class RateLimitingService:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def get_user_subscription(self, user_id: str) -> Optional[Dict]:
        """Get user's current subscription details"""
        try:
            result = self.supabase.table('user_subscriptions').select(
                '''
                id, status, started_at, expires_at,
                subscription_plans!inner(
                    id, name, display_name, daily_query_limit, 
                    price_monthly, features
                )
                '''
            ).eq('user_id', user_id).eq('status', 'active').single().execute()
            
            if result.data:
                subscription = result.data
                plan = subscription['subscription_plans']
                return {
                    'subscription_id': subscription['id'],
                    'plan_name': plan['name'],
                    'plan_display_name': plan['display_name'],
                    'daily_limit': plan['daily_query_limit'],
                    'price_monthly': plan['price_monthly'],
                    'features': plan['features'],
                    'status': subscription['status'],
                    'expires_at': subscription['expires_at']
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user subscription: {str(e)}")
            return None
    
    async def get_daily_usage(self, user_id: str, target_date: date = None) -> int:
        """Get user's query count for a specific date (defaults to today)"""
        if target_date is None:
            target_date = date.today()
        
        try:
            result = self.supabase.table('daily_query_usage').select(
                'query_count'
            ).eq('user_id', user_id).eq('usage_date', target_date.isoformat()).single().execute()
            
            return result.data['query_count'] if result.data else 0
        except Exception as e:
            # If no record exists, return 0
            return 0
    
    async def increment_daily_usage(self, user_id: str) -> int:
        """Increment user's daily query count and return new count"""
        today = date.today()
        
        try:
            # Try to increment existing record
            result = self.supabase.table('daily_query_usage').select(
                'id, query_count'
            ).eq('user_id', user_id).eq('usage_date', today.isoformat()).execute()
            
            if result.data:
                # Update existing record
                record = result.data[0]
                new_count = record['query_count'] + 1
                
                self.supabase.table('daily_query_usage').update({
                    'query_count': new_count,
                    'updated_at': datetime.now().isoformat()
                }).eq('id', record['id']).execute()
                
                return new_count
            else:
                # Create new record
                self.supabase.table('daily_query_usage').insert({
                    'user_id': user_id,
                    'usage_date': today.isoformat(),
                    'query_count': 1
                }).execute()
                
                return 1
                
        except Exception as e:
            logger.error(f"Error incrementing daily usage: {str(e)}")
            raise
    
    async def check_rate_limit(self, user_id: str) -> Tuple[bool, Dict]:
        """
        Check if user can make another query
        Returns: (can_proceed, info_dict)
        """
        subscription = await self.get_user_subscription(user_id)
        
        if not subscription:
            # No subscription found, assign default free plan
            await self._assign_free_plan(user_id)
            subscription = await self.get_user_subscription(user_id)
        
        # Check if subscription is active
        if subscription['status'] != 'active':
            return False, {
                'error': 'subscription_inactive',
                'message': 'Your subscription is not active',
                'subscription': subscription
            }
        
        # Check if subscription has expired
        if subscription['expires_at']:
            expires_at = datetime.fromisoformat(subscription['expires_at'].replace('Z', '+00:00'))
            if expires_at < datetime.now():
                return False, {
                    'error': 'subscription_expired',
                    'message': 'Your subscription has expired',
                    'subscription': subscription
                }
        
        daily_limit = subscription['daily_limit']
        
        # Unlimited queries for premium users
        if daily_limit == -1:
            return True, {
                'unlimited': True,
                'subscription': subscription
            }
        
        # Check daily usage for limited plans
        current_usage = await self.get_daily_usage(user_id)
        
        if current_usage >= daily_limit:
            return False, {
                'error': 'daily_limit_exceeded',
                'message': f'Daily query limit of {daily_limit} reached',
                'current_usage': current_usage,
                'daily_limit': daily_limit,
                'subscription': subscription
            }
        
        return True, {
            'current_usage': current_usage,
            'daily_limit': daily_limit,
            'remaining': daily_limit - current_usage,
            'subscription': subscription
        }
    
    async def _assign_free_plan(self, user_id: str):
        """Assign free plan to user if they don't have a subscription"""
        try:
            # Get free plan ID
            plan_result = self.supabase.table('subscription_plans').select(
                'id'
            ).eq('name', 'free').single().execute()
            
            if plan_result.data:
                self.supabase.table('user_subscriptions').insert({
                    'user_id': user_id,
                    'plan_id': plan_result.data['id'],
                    'status': 'active'
                }).execute()
        except Exception as e:
            logger.error(f"Error assigning free plan: {str(e)}")
    
    async def get_subscription_plans(self) -> list:
        """Get all available subscription plans"""
        try:
            result = self.supabase.table('subscription_plans').select(
                'id, name, display_name, daily_query_limit, price_monthly, features'
            ).eq('is_active', True).order('price_monthly').execute()
            
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting subscription plans: {str(e)}")
            return []
    
    async def upgrade_user_subscription(self, user_id: str, plan_name: str) -> bool:
        """Upgrade user to a specific plan"""
        try:
            # Get plan details
            plan_result = self.supabase.table('subscription_plans').select(
                'id'
            ).eq('name', plan_name).eq('is_active', True).single().execute()
            
            if not plan_result.data:
                return False
            
            plan_id = plan_result.data['id']
            
            # Update or create subscription
            self.supabase.table('user_subscriptions').upsert({
                'user_id': user_id,
                'plan_id': plan_id,
                'status': 'active',
                'started_at': datetime.now().isoformat(),
                'expires_at': None,  # Set based on your billing cycle
                'updated_at': datetime.now().isoformat()
            }).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error upgrading subscription: {str(e)}")
            return False
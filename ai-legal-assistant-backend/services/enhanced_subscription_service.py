import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from config.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class EnhancedSubscriptionService:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.logger = logging.getLogger(__name__)
    
    async def get_user_subscription_with_features(self, user_id: str) -> Dict[str, Any]:
        """Get user subscription with all plan features"""
        try:
            # Get user subscription with plan details
            result = self.supabase.table('user_subscriptions').select(
                '''
                subscription_id,
                plan_id,
                status,
                started_at,
                subscription_plans!user_subscriptions_plan_id_fkey(
                    id,
                    name,
                    display_name,
                    daily_query_limit,
                    max_document_size_mb,
                    max_documents_per_user,
                    price_monthly,
                    features,
                    is_active
                )
                '''
            ).eq('user_id', user_id).eq('status', 'active').execute()

            if result.data and len(result.data) > 0:
                subscription = result.data[0]
                plan = subscription['subscription_plans']
                
                return {
                    'subscription_id': subscription['subscription_id'],
                    'plan_id': plan['id'],
                    'plan_name': plan['name'],
                    'plan_display_name': plan['display_name'],
                    'daily_limit': plan['daily_query_limit'],
                    'max_document_size_mb': plan['max_document_size_mb'],
                    'max_documents_per_user': plan['max_documents_per_user'],
                    'price_monthly': plan['price_monthly'],
                    'features': plan['features'],
                    'status': subscription['status'],
                    'started_at': subscription['started_at'],
                    'is_unlimited': plan['daily_query_limit'] == -1
                }
            else:
                return await self._get_default_free_plan()
                
        except Exception as e:
            self.logger.error(f"Error getting user subscription: {str(e)}")
            return await self._get_default_free_plan()
    
    async def _get_default_free_plan(self) -> Dict[str, Any]:
        """Get default free plan when no subscription exists"""
        try:
            # Try to get free plan from database
            result = self.supabase.table('subscription_plans').select('*').eq('name', 'free').eq('is_active', True).execute()
            
            if result.data and len(result.data) > 0:
                plan = result.data[0]
                return {
                    'subscription_id': None,
                    'plan_id': plan['id'],
                    'plan_name': plan['name'],
                    'plan_display_name': plan['display_name'],
                    'daily_limit': plan['daily_query_limit'],
                    'max_document_size_mb': plan['max_document_size_mb'],
                    'max_documents_per_user': plan['max_documents_per_user'],
                    'price_monthly': plan['price_monthly'],
                    'features': plan['features'],
                    'status': 'active',
                    'started_at': datetime.utcnow().isoformat(),
                    'is_unlimited': plan['daily_query_limit'] == -1
                }
        except Exception as e:
            self.logger.error(f"Error getting free plan: {str(e)}")
            
        # Return hardcoded free plan as fallback
        return {
            'subscription_id': None,
            'plan_id': None,
            'plan_name': 'free',
            'plan_display_name': 'Free Plan',
            'daily_limit': 10,
            'max_document_size_mb': 10,
            'max_documents_per_user': 5,
            'price_monthly': 0.00,
            'features': ['Basic queries', 'Public documents'],
            'status': 'active',
            'started_at': datetime.utcnow().isoformat(),
            'is_unlimited': False
        }
    
    async def get_daily_usage_detailed(self, user_id: str, target_date: date = None) -> Dict[str, Any]:
        """Get detailed daily usage statistics"""
        try:
            if target_date is None:
                target_date = date.today()
            
            # Get daily usage count
            usage_result = self.supabase.table('daily_query_usage').select(
                'query_count'
            ).eq('user_id', user_id).eq('usage_date', target_date.isoformat()).execute()
            
            current_usage = 0
            if usage_result.data and len(usage_result.data) > 0:
                current_usage = usage_result.data[0]['query_count']
            
            # Get user subscription limits
            subscription = await self.get_user_subscription_with_features(user_id)
            daily_limit = subscription['daily_limit']
            
            return {
                'date': target_date.isoformat(),
                'current_usage': current_usage,
                'daily_limit': daily_limit,
                'remaining': daily_limit - current_usage if daily_limit != -1 else -1,
                'is_unlimited': daily_limit == -1,
                'percentage_used': round((current_usage / daily_limit) * 100, 2) if daily_limit > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting daily usage: {str(e)}")
            return {
                'date': target_date.isoformat() if target_date else date.today().isoformat(),
                'current_usage': 0,
                'daily_limit': 10,
                'remaining': 10,
                'is_unlimited': False,
                'percentage_used': 0
            }

    async def get_user_subscription_details(self, user_id: str) -> Optional[Dict]:
        """Get user's current subscription with all limits"""
        try:
            result = self.supabase.table('user_subscriptions').select(
                '''
                id,
                plan_id,
                status,
                expires_at,
                subscription_plans!user_subscriptions_plan_id_fkey(
                    id,
                    name,
                    display_name,
                    daily_query_limit,
                    max_document_size_mb,
                    max_documents_per_user,
                    features,
                    price_monthly
                )
                '''
            ).eq('user_id', user_id).eq('status', 'active').execute()
            
            if result.data and len(result.data) > 0:
                subscription = result.data[0]
                plan = subscription['subscription_plans']
                
                return {
                    'plan_id': plan['id'],
                    'plan_name': plan['name'],
                    'display_name': plan['display_name'],
                    'daily_query_limit': plan['daily_query_limit'],
                    'max_document_size_mb': plan['max_document_size_mb'],
                    'max_documents_per_user': plan['max_documents_per_user'],
                    'features': plan['features'],
                    'price_monthly': plan['price_monthly'],
                    'status': subscription['status'],
                    'expires_at': subscription['expires_at']
                }
            else:
                # Assign free plan if no subscription
                return await self._assign_free_plan(user_id)
                
        except Exception as e:
            self.logger.error(f"Error getting user subscription: {str(e)}")
            return None

    async def check_document_size_limit(self, user_id: str, document_size_mb: float) -> bool:
        """Check if document size is within user's package limit"""
        subscription = await self.get_user_subscription_details(user_id)
        if not subscription:
            return False
        return document_size_mb <= subscription['max_document_size_mb']

    async def check_document_count_limit(self, user_id: str) -> bool:
        """Check if user can upload more documents"""
        subscription = await self.get_user_subscription_details(user_id)
        if not subscription:
            return False
        
        current_storage = await self.get_user_storage_info(user_id)
        return current_storage['document_count'] < subscription['max_documents_per_user']

    async def get_user_storage_info(self, user_id: str) -> Dict:
        """Get user's current storage usage"""
        try:
            result = self.supabase.table('user_document_storage').select(
                'document_count, total_storage_mb'
            ).eq('user_id', user_id).execute()
            
            if result.data and len(result.data) > 0:
                storage = result.data[0]
                return {
                    'document_count': storage['document_count'],
                    'total_storage_mb': float(storage['total_storage_mb'])
                }
            else:
                return {'document_count': 0, 'total_storage_mb': 0.0}
        except Exception as e:
            self.logger.error(f"Error getting storage info: {str(e)}")
            return {'document_count': 0, 'total_storage_mb': 0.0}

    async def update_user_storage(self, user_id: str, document_size_mb: float, increment: bool = True) -> bool:
        """Update user's storage usage"""
        try:
            # Check if record exists
            existing = self.supabase.table('user_document_storage').select('*').eq('user_id', user_id).execute()
            
            if existing.data and len(existing.data) > 0:
                # Update existing record
                current = existing.data[0]
                new_count = current['document_count'] + (1 if increment else -1)
                new_storage = current['total_storage_mb'] + (document_size_mb if increment else -document_size_mb)
                
                result = self.supabase.table('user_document_storage').update({
                    'document_count': max(0, new_count),
                    'total_storage_mb': max(0, new_storage),
                    'last_updated': datetime.utcnow().isoformat()
                }).eq('user_id', user_id).execute()
            else:
                # Create new record
                result = self.supabase.table('user_document_storage').insert({
                    'user_id': user_id,
                    'document_count': 1 if increment else 0,
                    'total_storage_mb': document_size_mb if increment else 0,
                    'last_updated': datetime.utcnow().isoformat()
                }).execute()
            
            return bool(result.data)
        except Exception as e:
            self.logger.error(f"Error updating storage: {str(e)}")
            return False

    async def _assign_free_plan(self, user_id: str) -> Dict:
        """Assign free plan to user if no subscription exists"""
        try:
            # Get free plan
            free_plan_result = self.supabase.table('subscription_plans').select('*').eq('name', 'free').eq('is_active', True).execute()
            
            if not free_plan_result.data:
                # Return hardcoded free plan if not found in database
                return {
                    'plan_name': 'free',
                    'display_name': 'Free Plan',
                    'daily_query_limit': 10,
                    'max_document_size_mb': 5,
                    'max_documents_per_user': 10,
                    'features': ['Basic queries'],
                    'status': 'active',
                    'expires_at': None
                }
            
            free_plan = free_plan_result.data[0]
            
            # Create subscription
            self.supabase.table('user_subscriptions').insert({
                'user_id': user_id,
                'plan_id': free_plan['id'],
                'status': 'active',
                'started_at': datetime.utcnow().isoformat()
            }).execute()
            
            return {
                'plan_id': free_plan['id'],
                'plan_name': free_plan['name'],
                'display_name': free_plan['display_name'],
                'daily_query_limit': free_plan['daily_query_limit'],
                'max_document_size_mb': free_plan['max_document_size_mb'],
                'max_documents_per_user': free_plan['max_documents_per_user'],
                'features': free_plan['features'],
                'status': 'active',
                'expires_at': None
            }
        except Exception as e:
            self.logger.error(f"Error assigning free plan: {str(e)}")
            return {
                'plan_name': 'free',
                'display_name': 'Free Plan',
                'daily_query_limit': 10,
                'max_document_size_mb': 5,
                'max_documents_per_user': 10,
                'features': ['Basic queries'],
                'status': 'active',
                'expires_at': None
            }

    async def get_daily_usage(self, user_id: str, usage_date: date = None) -> Dict:
        """Get user's daily query usage"""
        if usage_date is None:
            usage_date = date.today()
        
        try:
            result = self.supabase.table('daily_query_usage').select(
                'query_count'
            ).eq('user_id', user_id).eq('usage_date', usage_date.isoformat()).execute()
            
            return {
                'user_id': user_id,
                'usage_date': usage_date,
                'query_count': result.data[0]['query_count'] if result.data else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting daily usage: {str(e)}")
            return {'query_count': 0}

    async def check_daily_query_limit(self, user_id: str) -> bool:
        """Check if user can make more queries today"""
        subscription = await self.get_user_subscription_details(user_id)
        if not subscription:
            return False
        
        # -1 means unlimited
        if subscription['daily_query_limit'] == -1:
            return True
        
        today_usage = await self.get_daily_usage(user_id)
        return today_usage['query_count'] < subscription['daily_query_limit']

    async def increment_query_usage(self, user_id: str) -> bool:
        """Increment user's daily query count"""
        try:
            # Check if record exists for today
            today = date.today()
            existing = self.supabase.table('daily_query_usage').select('*').eq('user_id', user_id).eq('usage_date', today.isoformat()).execute()
            
            if existing.data and len(existing.data) > 0:
                # Update existing record
                current_count = existing.data[0]['query_count']
                result = self.supabase.table('daily_query_usage').update({
                    'query_count': current_count + 1,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('user_id', user_id).eq('usage_date', today.isoformat()).execute()
            else:
                # Create new record
                result = self.supabase.table('daily_query_usage').insert({
                    'user_id': user_id,
                    'usage_date': today.isoformat(),
                    'query_count': 1,
                    'updated_at': datetime.utcnow().isoformat()
                }).execute()
            
            return bool(result.data)
        except Exception as e:
            self.logger.error(f"Error incrementing query usage: {str(e)}")
            return False

    async def get_comprehensive_usage_stats(self, user_id: str) -> Dict:
        """Get complete usage statistics for user"""
        subscription = await self.get_user_subscription_details(user_id)
        storage_info = await self.get_user_storage_info(user_id)
        today_usage = await self.get_daily_usage(user_id)
        
        return {
            'subscription': subscription,
            'storage_usage': storage_info,
            'daily_usage': today_usage,
            'limits': {
                'remaining_documents': (
                    subscription['max_documents_per_user'] - storage_info['document_count']
                    if subscription else 0
                ),
                'remaining_queries': (
                    subscription['daily_query_limit'] - today_usage['query_count']
                    if subscription and subscription['daily_query_limit'] != -1 
                    else -1
                ),
                'remaining_storage_mb': (
                    subscription['max_document_size_mb'] - storage_info['total_storage_mb']
                    if subscription else 0
                )
            }
        }

    async def get_usage_history(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get user's usage history for specified number of days"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            result = self.supabase.table('daily_query_usage').select(
                'usage_date, query_count'
            ).eq('user_id', user_id).gte(
                'usage_date', start_date.isoformat()
            ).lte(
                'usage_date', end_date.isoformat()
            ).order('usage_date', desc=True).execute()
            
            return result.data or []
            
        except Exception as e:
            self.logger.error(f"Error getting usage history: {str(e)}")
            return []
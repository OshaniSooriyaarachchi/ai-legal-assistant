import logging
from typing import Dict, List, Optional
from datetime import datetime
from config.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class AdminPackageService:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.logger = logging.getLogger(__name__)
    
    async def create_custom_package(self, admin_user_id: str, package_data: Dict) -> str:
        """Create a new custom package by admin"""
        try:
            result = self.supabase.table('subscription_plans').insert({
                'name': package_data['name'],
                'display_name': package_data['display_name'],
                'daily_query_limit': package_data['daily_query_limit'],
                'max_document_size_mb': package_data.get('max_document_size_mb'),
                'max_documents_per_user': package_data.get('max_documents_per_user'),
                'price_monthly': package_data['price_monthly'],
                'features': package_data['features'],
                'created_by': admin_user_id,
                'is_custom': True,
                'is_active': package_data.get('is_active', True)
            }).execute()
            
            if result.data and len(result.data) > 0:
                package_id = result.data[0]['id']
                self.logger.info(f"Created custom package: {package_id}")
                return package_id
            else:
                raise Exception("Failed to create package - no data returned")
                
        except Exception as e:
            self.logger.error(f"Error creating custom package: {str(e)}")
            raise Exception(f"Failed to create package: {str(e)}")
    
    async def update_package(self, package_id: str, admin_user_id: str, package_data: Dict) -> bool:
        """Update an existing package"""
        try:
            # Check if admin can modify this package (only custom packages or system admin)
            check_result = self.supabase.table('subscription_plans').select(
                'created_by, is_custom'
            ).eq('id', package_id).execute()
            
            if not check_result.data or len(check_result.data) == 0:
                raise Exception("Package not found")
            
            package_info = check_result.data[0]
            created_by = package_info['created_by']
            is_custom = package_info['is_custom']
            
            if is_custom and str(created_by) != admin_user_id:
                raise Exception("You can only modify packages you created")
            
            # Update the package
            result = self.supabase.table('subscription_plans').update({
                'name': package_data['name'],
                'display_name': package_data['display_name'],
                'daily_query_limit': package_data['daily_query_limit'],
                'max_document_size_mb': package_data.get('max_document_size_mb'),
                'max_documents_per_user': package_data.get('max_documents_per_user'),
                'price_monthly': package_data['price_monthly'],
                'features': package_data['features'],
                'is_active': package_data.get('is_active', True),
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', package_id).execute()
            
            if result.data:
                self.logger.info(f"Updated package: {package_id}")
                return True
            else:
                raise Exception("No rows updated")
                
        except Exception as e:
            self.logger.error(f"Error updating package: {str(e)}")
            raise Exception(f"Failed to update package: {str(e)}")
    
    async def delete_package(self, package_id: str, admin_user_id: str) -> bool:
        """Delete a custom package (soft delete by deactivating)"""
        try:
            # Check if there are active subscriptions
            active_subs_result = self.supabase.table('user_subscriptions').select(
                'id'
            ).eq('plan_id', package_id).eq('status', 'active').execute()
            
            active_subscriptions = len(active_subs_result.data) if active_subs_result.data else 0
            
            if active_subscriptions > 0:
                raise Exception(f"Cannot delete package with {active_subscriptions} active subscriptions")
            
            # Deactivate the package
            result = self.supabase.table('subscription_plans').update({
                'is_active': False,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', package_id).execute()
            
            # Note: Supabase doesn't have the same row-level security check as the SQL version
            # You might want to add additional checks here based on your RLS policies
            
            if result.data:
                self.logger.info(f"Deactivated package: {package_id}")
                return True
            else:
                raise Exception("Package not found or you don't have permission to delete it")
                
        except Exception as e:
            self.logger.error(f"Error deleting package: {str(e)}")
            raise Exception(f"Failed to delete package: {str(e)}")
    
    async def get_all_packages(self, admin_user_id: str = None) -> List[Dict]:
        """Get all packages (admin can see all, regular users see only active)"""
        try:
            if admin_user_id:
                # Admin sees all packages - we'll need to do this in multiple queries due to Supabase limitations
                packages_result = self.supabase.table('subscription_plans').select(
                    '*'
                ).order('is_custom', desc=False).order('created_at', desc=True).execute()
                
                packages = packages_result.data if packages_result.data else []
                
                # Add active subscription count for each package
                for package in packages:
                    subs_result = self.supabase.table('user_subscriptions').select(
                        'id'
                    ).eq('plan_id', package['id']).eq('status', 'active').execute()
                    
                    package['active_subscriptions'] = len(subs_result.data) if subs_result.data else 0
                    
                    # Try to get creator email if available
                    if package.get('created_by'):
                        try:
                            # Note: You might need to adjust this based on your auth table structure
                            user_result = self.supabase.table('auth.users').select(
                                'email'
                            ).eq('id', package['created_by']).execute()
                            
                            if user_result.data and len(user_result.data) > 0:
                                package['created_by_email'] = user_result.data[0]['email']
                        except:
                            # If we can't get the email, just skip it
                            package['created_by_email'] = None
                
                return packages
                
            else:
                # Regular users see only active packages
                result = self.supabase.table('subscription_plans').select(
                    '*'
                ).eq('is_active', True).order('price_monthly', desc=False).execute()
                
                return result.data if result.data else []
                
        except Exception as e:
            self.logger.error(f"Error getting packages: {str(e)}")
            return []
    
    async def assign_package_to_user(self, user_id: str, package_id: str, admin_user_id: str) -> bool:
        """Assign a package to a user"""
        try:
            # Verify package exists and is active
            package_result = self.supabase.table('subscription_plans').select(
                'name'
            ).eq('id', package_id).eq('is_active', True).execute()
            
            if not package_result.data or len(package_result.data) == 0:
                raise Exception("Package not found or inactive")
            
            # Check if user already has a subscription
            existing_sub_result = self.supabase.table('user_subscriptions').select(
                'id'
            ).eq('user_id', user_id).execute()
            
            current_time = datetime.utcnow().isoformat()
            
            if existing_sub_result.data and len(existing_sub_result.data) > 0:
                # Update existing subscription
                result = self.supabase.table('user_subscriptions').update({
                    'plan_id': package_id,
                    'status': 'active',
                    'started_at': current_time,
                    'updated_at': current_time
                }).eq('user_id', user_id).execute()
            else:
                # Create new subscription
                result = self.supabase.table('user_subscriptions').insert({
                    'user_id': user_id,
                    'plan_id': package_id,
                    'status': 'active',
                    'started_at': current_time,
                    'created_at': current_time,
                    'updated_at': current_time
                }).execute()
            
            if result.data:
                self.logger.info(f"Assigned package {package_id} to user {user_id}")
                return True
            else:
                raise Exception("Failed to assign package")
                
        except Exception as e:
            self.logger.error(f"Error assigning package: {str(e)}")
            raise Exception(f"Failed to assign package: {str(e)}")
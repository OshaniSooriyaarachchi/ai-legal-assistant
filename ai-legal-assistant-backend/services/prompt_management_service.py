import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from config.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class PromptManagementService:
    """Service for managing dynamic prompt templates"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def verify_admin_role(self, user_id: str) -> bool:
        """Check if user has admin privileges"""
        try:
            result = self.supabase.table('user_roles').select('role').eq('user_id', user_id).eq('role', 'admin').eq('is_active', True).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error verifying admin role: {str(e)}")
            return False
    
    async def get_prompt_template(self, name: str, user_type: str = 'normal') -> Optional[Dict]:
        """Get a specific prompt template by name with proper fallback logic"""
        try:
            # First try to get user-type specific prompt
            result = self.supabase.table('prompt_templates').select('*').eq('name', name).eq('user_type', user_type).eq('is_active', True).execute()
            if result.data:
                logger.info(f"Found template {name} for user_type {user_type}")
                return result.data[0]
            
            # Fallback to general prompt
            result = self.supabase.table('prompt_templates').select('*').eq('name', name).eq('user_type', 'all').eq('is_active', True).execute()
            
            if result.data:
                logger.info(f"Found template {name} for user_type 'all' (fallback)")
                return result.data[0]
            
            logger.warning(f"Template {name} not found for user_type {user_type} or 'all'")
            return None
            
        except Exception as e:
            logger.error(f"Error getting prompt template {name}: {str(e)}")
            return None
    
    async def get_all_prompt_templates(self, admin_user_id: str = None) -> List[Dict]:
        """Get all prompt templates (admin can see all, regular users see only active)"""
        try:
            if admin_user_id and await self.verify_admin_role(admin_user_id):
                # Admin sees all prompts
                result = self.supabase.table('prompt_templates').select('*').order('category', desc=False).order('name', desc=False).execute()
            else:
                # Regular users see only active prompts
                result = self.supabase.table('prompt_templates').select('*').eq('is_active', True).order('category', desc=False).order('name', desc=False).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting all prompt templates: {str(e)}")
            return []
    
    async def create_prompt_template(self, admin_user_id: str, prompt_data: Dict) -> str:
        """Create a new prompt template"""
        try:
            # Verify admin privileges
            if not await self.verify_admin_role(admin_user_id):
                raise Exception("Admin privileges required")
            
            # Validate required fields
            required_fields = ['name', 'title', 'template_content', 'category']
            for field in required_fields:
                if field not in prompt_data:
                    raise Exception(f"Missing required field: {field}")
            
            # Check if prompt name already exists
            existing = self.supabase.table('prompt_templates').select('id').eq('name', prompt_data['name']).execute()
            if existing.data:
                raise Exception(f"Prompt template with name '{prompt_data['name']}' already exists")
            
            # Create prompt template
            insert_data = {
                'name': prompt_data['name'],
                'title': prompt_data['title'],
                'description': prompt_data.get('description', ''),
                'template_content': prompt_data['template_content'],
                'placeholders': prompt_data.get('placeholders', []),
                'category': prompt_data['category'],
                'user_type': prompt_data.get('user_type', 'all'),
                'is_active': prompt_data.get('is_active', True),
                'created_by': admin_user_id,
                'updated_by': admin_user_id
            }
            
            result = self.supabase.table('prompt_templates').insert(insert_data).execute()
            
            if not result.data:
                raise Exception("Failed to create prompt template")
            
            template_id = result.data[0]['id']
            logger.info(f"Created prompt template {prompt_data['name']} with ID {template_id}")
            return template_id
            
        except Exception as e:
            logger.error(f"Error creating prompt template: {str(e)}")
            raise Exception(f"Failed to create prompt template: {str(e)}")
    
    async def update_prompt_template(self, admin_user_id: str, template_id: str, prompt_data: Dict) -> bool:
        """Update an existing prompt template"""
        try:
            # Verify admin privileges
            if not await self.verify_admin_role(admin_user_id):
                raise Exception("Admin privileges required")
            
            # Get existing template
            existing_result = self.supabase.table('prompt_templates').select('*').eq('id', template_id).execute()
            if not existing_result.data:
                raise Exception("Prompt template not found")
            
            existing_template = existing_result.data[0]
            
            # Prepare update data
            update_data = {
                'updated_by': admin_user_id,
                'updated_at': datetime.now().isoformat()
            }
            
            # Only update provided fields
            updatable_fields = ['title', 'description', 'template_content', 'placeholders', 'category', 'user_type', 'is_active']
            for field in updatable_fields:
                if field in prompt_data:
                    update_data[field] = prompt_data[field]
            
            # Update the template
            result = self.supabase.table('prompt_templates').update(update_data).eq('id', template_id).execute()
            
            if not result.data:
                raise Exception("Failed to update prompt template")
            
            logger.info(f"Updated prompt template {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating prompt template: {str(e)}")
            raise Exception(f"Failed to update prompt template: {str(e)}")
    
    async def delete_prompt_template(self, admin_user_id: str, template_id: str) -> bool:
        """Delete a prompt template (soft delete by setting is_active=False)"""
        try:
            # Verify admin privileges
            if not await self.verify_admin_role(admin_user_id):
                raise Exception("Admin privileges required")
            
            # Soft delete by setting is_active=False
            result = self.supabase.table('prompt_templates').update({
                'is_active': False,
                'updated_by': admin_user_id,
                'updated_at': datetime.now().isoformat()
            }).eq('id', template_id).execute()
            
            if not result.data:
                raise Exception("Prompt template not found")
            
            logger.info(f"Deleted prompt template {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting prompt template: {str(e)}")
            raise Exception(f"Failed to delete prompt template: {str(e)}")
    
    async def get_prompt_template_versions(self, admin_user_id: str, template_id: str) -> List[Dict]:
        """Get version history for a prompt template"""
        try:
            # Verify admin privileges
            if not await self.verify_admin_role(admin_user_id):
                raise Exception("Admin privileges required")
            
            result = self.supabase.table('prompt_template_versions').select('*').eq('template_id', template_id).order('version_number', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting prompt template versions: {str(e)}")
            raise Exception(f"Failed to get prompt template versions: {str(e)}")
    
    async def restore_prompt_version(self, admin_user_id: str, template_id: str, version_number: int) -> bool:
        """Restore a prompt template to a previous version"""
        try:
            # Verify admin privileges
            if not await self.verify_admin_role(admin_user_id):
                raise Exception("Admin privileges required")
            
            # Get the version to restore
            version_result = self.supabase.table('prompt_template_versions').select('*').eq('template_id', template_id).eq('version_number', version_number).execute()
            
            if not version_result.data:
                raise Exception(f"Version {version_number} not found")
            
            version_data = version_result.data[0]
            
            # Update the current template with the version data
            update_data = {
                'template_content': version_data['template_content'],
                'placeholders': version_data['placeholders'],
                'updated_by': admin_user_id,
                'updated_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('prompt_templates').update(update_data).eq('id', template_id).execute()
            
            if not result.data:
                raise Exception("Failed to restore prompt template")
            
            logger.info(f"Restored prompt template {template_id} to version {version_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring prompt version: {str(e)}")
            raise Exception(f"Failed to restore prompt version: {str(e)}")
    
    async def format_prompt(self, template_name: str, variables: Dict[str, Any], user_type: str = 'normal') -> str:
        """Format a prompt template with the provided variables"""
        try:
            # Get the template
            template = await self.get_prompt_template(template_name, user_type)
            if not template:
                logger.warning(f"Template {template_name} not found, using fallback")
                return self._get_fallback_prompt(template_name, variables)
            
            # Format the template content
            template_content = template['template_content']
            
            # Handle optional variables by providing empty strings for missing ones
            formatted_variables = {}
            for key, value in variables.items():
                if value is not None:
                    formatted_variables[key] = str(value)
                else:
                    formatted_variables[key] = ''
            
            # Add empty strings for missing placeholders to avoid KeyError
            placeholders = template.get('placeholders', [])
            if isinstance(placeholders, list):
                for placeholder in placeholders:
                    if placeholder not in formatted_variables:
                        formatted_variables[placeholder] = ''
            
            # Format the template
            try:
                formatted_prompt = template_content.format(**formatted_variables)
                return formatted_prompt
            except KeyError as ke:
                logger.error(f"Missing variable {ke} for template {template_name}")
                # Provide empty string for missing variables
                template_content_safe = template_content
                for placeholder in placeholders:
                    if placeholder not in formatted_variables:
                        template_content_safe = template_content_safe.replace(f'{{{placeholder}}}', '')
                
                return template_content_safe.format(**formatted_variables)
            
        except Exception as e:
            logger.error(f"Error formatting prompt {template_name}: {str(e)}")
            return self._get_fallback_prompt(template_name, variables)
    
    def _get_fallback_prompt(self, template_name: str, variables: Dict[str, Any]) -> str:
        """Provide fallback prompts in case database templates are unavailable"""
        fallback_prompts = {
            'rag_prompt': f"""You are an AI legal assistant. Based on the provided context, please answer the following question:

Context: {variables.get('context', '')}
Question: {variables.get('query', '')}

Please provide a helpful response based on the available information.""",
            
            'document_summary_prompt': f"""Please provide a summary of the following document:

{variables.get('document_text', '')}

Summary:""",
            
            'chat_title_generation': f"""Generate a concise title for a chat that starts with: "{variables.get('message', '')}"
            
Requirements: Maximum 50 characters, focus on the main topic."""
        }
        
        return fallback_prompts.get(template_name, f"Template {template_name} not available. Please contact support.")
    
    async def duplicate_prompt_template(self, admin_user_id: str, template_id: str, new_name: str) -> str:
        """Duplicate an existing prompt template"""
        try:
            # Verify admin privileges
            if not await self.verify_admin_role(admin_user_id):
                raise Exception("Admin privileges required")
            
            # Get existing template
            existing_result = self.supabase.table('prompt_templates').select('*').eq('id', template_id).execute()
            if not existing_result.data:
                raise Exception("Source prompt template not found")
            
            source_template = existing_result.data[0]
            
            # Check if new name already exists
            name_check = self.supabase.table('prompt_templates').select('id').eq('name', new_name).execute()
            if name_check.data:
                raise Exception(f"Prompt template with name '{new_name}' already exists")
            
            # Create duplicate
            duplicate_data = {
                'name': new_name,
                'title': f"{source_template['title']} (Copy)",
                'description': source_template.get('description', ''),
                'template_content': source_template['template_content'],
                'placeholders': source_template.get('placeholders', []),
                'category': source_template['category'],
                'user_type': source_template['user_type'],
                'is_active': True,
                'created_by': admin_user_id,
                'updated_by': admin_user_id
            }
            
            result = self.supabase.table('prompt_templates').insert(duplicate_data).execute()
            
            if not result.data:
                raise Exception("Failed to duplicate prompt template")
            
            new_template_id = result.data[0]['id']
            logger.info(f"Duplicated prompt template {template_id} to {new_template_id} with name {new_name}")
            return new_template_id
            
        except Exception as e:
            logger.error(f"Error duplicating prompt template: {str(e)}")
            raise Exception(f"Failed to duplicate prompt template: {str(e)}")

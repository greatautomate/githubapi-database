import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional, Tuple
from app.config import Config

logger = logging.getLogger(__name__)

class GitHubAPI:
    def __init__(self, token: str, username: str = ""):
        self.token = token
        self.username = username
        self.base_url = "https://api.github.com"
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Visibility-Bot/1.0'
        }
        logger.debug(f"GitHubAPI initialized for user: {username}")

    async def validate_token(self) -> Tuple[bool, str]:
        """Validate GitHub token and get user info"""
        try:
            logger.info("🔍 Validating GitHub token...")

            async with aiohttp.ClientSession() as session:
                async with session.get(f'{self.base_url}/user', headers=self.headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        username = user_data.get('login', 'Unknown')
                        logger.info(f"✅ Token valid for user: {username}")
                        return True, username
                    else:
                        error_data = await response.json()
                        error_msg = error_data.get('message', f'HTTP {response.status}')
                        logger.error(f"❌ Token validation failed: {error_msg}")
                        return False, error_msg

        except Exception as e:
            logger.error(f"❌ Error validating token: {e}")
            return False, str(e)

    async def list_repositories(self) -> List[Dict]:
        """List all repositories for the authenticated user"""
        try:
            logger.info("📋 Fetching repositories...")
            repositories = []
            page = 1
            per_page = 100

            async with aiohttp.ClientSession() as session:
                while True:
                    url = f'{self.base_url}/user/repos?page={page}&per_page={per_page}&type=all&sort=updated'
                    logger.debug(f"Fetching page {page}...")

                    async with session.get(url, headers=self.headers) as response:
                        if response.status != 200:
                            logger.error(f"Failed to fetch repos: HTTP {response.status}")
                            break

                        repos = await response.json()
                        if not repos:
                            break

                        for repo in repos:
                            repositories.append({
                                'name': repo['name'],
                                'full_name': repo['full_name'],
                                'private': repo['private'],
                                'owner': repo['owner']['login'],
                                'description': repo.get('description', ''),
                                'url': repo['html_url'],
                                'created_at': repo['created_at'],
                                'updated_at': repo['updated_at'],
                                'size': repo['size'],
                                'language': repo.get('language', 'Unknown')
                            })

                        page += 1
                        if len(repos) < per_page:
                            break

                        # Small delay to avoid rate limiting
                        await asyncio.sleep(0.1)

            logger.info(f"✅ Found {len(repositories)} repositories")
            return repositories

        except Exception as e:
            logger.error(f"❌ Error listing repositories: {e}")
            return []

    async def get_repository(self, owner: str, repo_name: str) -> Optional[Dict]:
        """Get specific repository information"""
        try:
            logger.info(f"🔍 Getting repository: {owner}/{repo_name}")

            async with aiohttp.ClientSession() as session:
                url = f'{self.base_url}/repos/{owner}/{repo_name}'
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        repo_data = await response.json()
                        logger.info(f"✅ Repository found: {repo_data['full_name']}")
                        return {
                            'name': repo_data['name'],
                            'full_name': repo_data['full_name'],
                            'private': repo_data['private'],
                            'owner': repo_data['owner']['login'],
                            'description': repo_data.get('description', ''),
                            'url': repo_data['html_url'],
                            'created_at': repo_data['created_at'],
                            'updated_at': repo_data['updated_at'],
                            'size': repo_data['size'],
                            'language': repo_data.get('language', 'Unknown')
                        }
                    elif response.status == 404:
                        logger.warning(f"Repository not found: {owner}/{repo_name}")
                        return None
                    else:
                        error_data = await response.json()
                        logger.error(f"Error getting repo: {error_data}")
                        return None

        except Exception as e:
            logger.error(f"❌ Error getting repository: {e}")
            return None

    async def toggle_repository_visibility(self, owner: str, repo_name: str, make_private: bool) -> Tuple[bool, str]:
        """Toggle repository visibility"""
        try:
            visibility = "private" if make_private else "public"
            logger.info(f"🔄 Making {owner}/{repo_name} {visibility}...")

            async with aiohttp.ClientSession() as session:
                url = f'{self.base_url}/repos/{owner}/{repo_name}'
                data = {'private': make_private}

                async with session.patch(url, headers=self.headers, json=data) as response:
                    if response.status == 200:
                        message = f"Repository {repo_name} is now {visibility}"
                        logger.info(f"✅ {message}")
                        return True, message
                    else:
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get('message', f'HTTP {response.status}')
                        except:
                            error_msg = f'HTTP {response.status}'

                        logger.error(f"❌ Failed to toggle visibility: {error_msg}")
                        return False, error_msg

        except Exception as e:
            logger.error(f"❌ Error toggling repository visibility: {e}")
            return False, str(e)

    async def batch_toggle_visibility(self, repos: List[Tuple[str, str]], make_private: bool) -> Dict[str, Tuple[bool, str]]:
        """Batch toggle repository visibility"""
        logger.info(f"🔄 Batch toggling {len(repos)} repositories...")
        results = {}
        semaphore = asyncio.Semaphore(3)  # Limit concurrent requests

        async def toggle_single(owner: str, repo_name: str):
            async with semaphore:
                success, message = await self.toggle_repository_visibility(owner, repo_name, make_private)
                results[f"{owner}/{repo_name}"] = (success, message)
                await asyncio.sleep(0.2)  # Rate limiting

        tasks = [toggle_single(owner, repo_name) for owner, repo_name in repos]
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"✅ Batch operation completed: {len(results)} repositories processed")
        return results

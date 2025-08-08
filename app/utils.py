from typing import List, Dict, Tuple
from datetime import datetime

def format_repository_list(repositories: List[Dict], username: str) -> str:
    """Format repository list for display"""
    if not repositories:
        return "📋 **No repositories found**"

    public_repos = [repo for repo in repositories if not repo['private']]
    private_repos = [repo for repo in repositories if repo['private']]

    text = f"📋 **Repositories for {username}**\n\n"
    text += f"**📊 Summary:**\n"
    text += f"• Total: {len(repositories)} repositories\n"
    text += f"• 🔓 Public: {len(public_repos)}\n"
    text += f"• 🔒 Private: {len(private_repos)}\n\n"

    if private_repos:
        text += "🔒 **Private Repositories:**\n"
        for repo in private_repos[:15]:  # Show first 15
            desc = repo['description']
            if desc and len(desc) > 40:
                desc = desc[:40] + "..."
            elif not desc:
                desc = "No description"

            size_mb = round(repo['size'] / 1024, 2) if repo['size'] > 0 else 0
            text += f"• `{repo['name']}` ({size_mb}MB)\n"
            text += f"  {desc}\n"

        if len(private_repos) > 15:
            text += f"  ... and {len(private_repos) - 15} more private repos\n"
        text += "\n"

    if public_repos:
        text += "🔓 **Public Repositories:**\n"
        for repo in public_repos[:15]:  # Show first 15
            desc = repo['description']
            if desc and len(desc) > 40:
                desc = desc[:40] + "..."
            elif not desc:
                desc = "No description"

            size_mb = round(repo['size'] / 1024, 2) if repo['size'] > 0 else 0
            text += f"• `{repo['name']}` ({size_mb}MB)\n"
            text += f"  {desc}\n"

        if len(public_repos) > 15:
            text += f"  ... and {len(public_repos) - 15} more public repos\n"

    text += "\n💡 **Commands:**\n"
    text += "• `/public <repo-name>` - Make public\n"
    text += "• `/private <repo-name>` - Make private\n"
    text += "• `/repo_status <repo-name>` - Check status"

    return text

def format_logs(logs: List[Dict]) -> str:
    """Format activity logs for display"""
    if not logs:
        return "📋 **No recent activity**"

    text = ""

    for log in logs:
        timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
        formatted_time = timestamp.strftime("%m/%d %H:%M")

        status_icon = "✅" if log['status'] == 'success' else "❌"
        action_name = log['action'].replace('_', ' ').title()

        text += f"{status_icon} **{action_name}**\n"
        text += f"   📁 {log['repository']}\n"
        text += f"   🕐 {formatted_time}\n\n"

    return text

def parse_repository_list(repos_str: str, default_owner: str) -> List[Tuple[str, str]]:
    """Parse comma-separated repository list"""
    if not repos_str:
        return []

    repo_list = []
    repos = [repo.strip() for repo in repos_str.split(',') if repo.strip()]

    for repo in repos:
        if '/' in repo:
            owner, repo_name = repo.split('/', 1)
            repo_list.append((owner.strip(), repo_name.strip()))
        else:
            repo_list.append((default_owner, repo.strip()))

    return repo_list

def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    if not text:
        return ""

    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '&', '"', "'", '`']
    for char in dangerous_chars:
        text = text.replace(char, '')

    return text.strip()

def validate_github_token_format(token: str) -> bool:
    """Validate GitHub token format"""
    if not token:
        return False

    # GitHub personal access tokens start with 'ghp_' and are 40 characters long
    if token.startswith('ghp_') and len(token) == 40:
        return True

    # GitHub app tokens start with 'ghs_' and are 40 characters long
    if token.startswith('ghs_') and len(token) == 40:
        return True

    # Classic tokens are 40 character hex strings
    if len(token) == 40 and all(c in '0123456789abcdefABCDEF' for c in token):
        return True

    return False

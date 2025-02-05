from .models import UserSettings

def get_user_settings(user_id):
    """
    Retrieve user settings from the database.
    If no settings exist, creates a new record with default values.
    """
    return UserSettings.get_user_settings(user_id)

def update_user_settings(user_id, **settings):
    """
    Update user settings in the database.
    
    Args:
        user_id (str): The unique identifier for the user
        **settings: Keyword arguments containing settings to update
                   (blocked_sites, excluded_sites, categories)
    """
    user_settings = get_user_settings(user_id)
    user_settings.update_settings(**settings)
    return user_settings

def add_blocked_site(user_id, site):
    """Add a site to the user's blocked sites list."""
    user_settings = get_user_settings(user_id)
    blocked_sites = user_settings.get_blocked_sites()
    if site not in blocked_sites:
        blocked_sites.append(site)
        user_settings.set_blocked_sites(blocked_sites)

def remove_blocked_site(user_id, site):
    """Remove a site from the user's blocked sites list."""
    user_settings = get_user_settings(user_id)
    blocked_sites = user_settings.get_blocked_sites()
    if site in blocked_sites:
        blocked_sites.remove(site)
        user_settings.set_blocked_sites(blocked_sites)

def add_excluded_site(user_id, site):
    """Add a site to the user's excluded sites list."""
    user_settings = get_user_settings(user_id)
    excluded_sites = user_settings.get_excluded_sites()
    if site not in excluded_sites:
        excluded_sites.append(site)
        user_settings.set_excluded_sites(excluded_sites)

def remove_excluded_site(user_id, site):
    """Remove a site from the user's excluded sites list."""
    user_settings = get_user_settings(user_id)
    excluded_sites = user_settings.get_excluded_sites()
    if site in excluded_sites:
        excluded_sites.remove(site)
        user_settings.set_excluded_sites(excluded_sites)

def update_categories(user_id, categories):
    """Update the user's filtered categories."""
    user_settings = get_user_settings(user_id)
    user_settings.update_settings(categories=categories)

"""Factory for setting up dependency injection container with existing implementations"""

from .container import DIContainer
from .interfaces import IProgressTracker, IFileManager, IChromeManager, IStatsReporter, IConfig
from .adapters import (
    ProgressTrackerAdapter, 
    FileManagerAdapter, 
    ChromeManagerAdapter, 
    StatsReporterAdapter,
    NullProgressTracker,
    NullStatsReporter
)
from .config_impl import Config


def create_container_with_dependencies(
    chrome_manager=None,
    file_manager=None, 
    progress_tracker=None,
    stats_reporter=None,
    config=None
) -> DIContainer:
    """Create a DI container with all dependencies registered"""
    
    container = DIContainer()
    
    # Register config
    if config:
        container.register_instance(IConfig, config)
    else:
        container.register_instance(IConfig, Config.from_existing_config())
    
    # Register file manager
    if file_manager:
        container.register_instance(IFileManager, FileManagerAdapter(file_manager))
    else:
        raise ValueError("FileManager is required")
    
    # Register chrome manager
    if chrome_manager:
        container.register_instance(IChromeManager, ChromeManagerAdapter(chrome_manager))
    else:
        raise ValueError("ChromeManager is required")
    
    # Register progress tracker (can be None)
    if progress_tracker:
        container.register_instance(IProgressTracker, ProgressTrackerAdapter(progress_tracker))
    else:
        container.register_instance(IProgressTracker, NullProgressTracker())
    
    # Register stats reporter (can be None)
    if stats_reporter:
        container.register_instance(IStatsReporter, StatsReporterAdapter(stats_reporter))
    else:
        container.register_instance(IStatsReporter, NullStatsReporter())
    
    return container


def create_download_manager_factory(container: DIContainer):
    """Create a factory function for DownloadManager that uses the DI container"""
    
    def create_download_manager(driver, wait):
        from ..download_management.download_manager import DownloadManager
        
        return DownloadManager(
            driver=driver,
            wait=wait,
            progress_tracker=container.get(IProgressTracker),
            file_manager=container.get(IFileManager),
            chrome_manager=container.get(IChromeManager),
            stats_reporter=container.get(IStatsReporter)
        )
    
    return create_download_manager
#!/usr/bin/env python3
"""
Unit Tests for Dependency Injection System

Tests the DI container, factory functions, adapters, and interfaces to prevent
regressions in the core architectural dependency injection system.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from unittest import TestCase

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from packages.di.container import DIContainer
from packages.di.factory import create_container_with_dependencies, create_download_manager_factory
from packages.di.interfaces import IProgressTracker, IFileManager, IChromeManager, IStatsReporter, IConfig
from packages.di.adapters import (
    ProgressTrackerAdapter,
    FileManagerAdapter, 
    ChromeManagerAdapter,
    StatsReporterAdapter,
    NullProgressTracker,
    NullStatsReporter
)
from packages.di.config_impl import Config


class TestDIContainer(TestCase):
    """Test DIContainer core functionality"""
    
    def setUp(self):
        """Set up test container"""
        self.container = DIContainer()
        
        # Create dummy interface for testing
        class ITestService:
            def test_method(self):
                pass
        
        self.ITestService = ITestService
    
    def test_container_initialization(self):
        """Test container initializes with empty services and singletons"""
        container = DIContainer()
        self.assertEqual(len(container._services), 0)
        self.assertEqual(len(container._singletons), 0)
    
    def test_register_factory_non_singleton(self):
        """Test registering a factory function (non-singleton)"""
        mock_factory = Mock(return_value="test_instance")
        
        self.container.register_factory(self.ITestService, mock_factory, singleton=False)
        
        # Check service registration
        self.assertTrue(self.container.has(self.ITestService))
        service_info = self.container._services[self.ITestService.__name__]
        self.assertEqual(service_info['factory'], mock_factory)
        self.assertFalse(service_info['singleton'])
        self.assertEqual(service_info['type'], 'factory')
    
    def test_register_factory_singleton(self):
        """Test registering a factory function (singleton)"""
        mock_factory = Mock(return_value="singleton_instance")
        
        self.container.register_factory(self.ITestService, mock_factory, singleton=True)
        
        # Check service registration
        service_info = self.container._services[self.ITestService.__name__]
        self.assertTrue(service_info['singleton'])
        self.assertEqual(service_info['type'], 'factory')
    
    def test_register_instance(self):
        """Test registering a concrete instance"""
        test_instance = Mock()
        
        self.container.register_instance(self.ITestService, test_instance)
        
        # Check service registration
        self.assertTrue(self.container.has(self.ITestService))
        service_info = self.container._services[self.ITestService.__name__]
        self.assertTrue(service_info['singleton'])
        self.assertEqual(service_info['type'], 'instance')
        
        # Check instance storage
        self.assertEqual(self.container._singletons[self.ITestService.__name__], test_instance)
    
    def test_get_factory_non_singleton_creates_new_instances(self):
        """Test factory non-singleton creates new instance each time"""
        call_count = 0
        
        def mock_factory():
            nonlocal call_count
            call_count += 1
            return f"instance_{call_count}"
        
        self.container.register_factory(self.ITestService, mock_factory, singleton=False)
        
        # Get multiple instances
        instance1 = self.container.get(self.ITestService)
        instance2 = self.container.get(self.ITestService)
        
        # Should be different instances
        self.assertEqual(instance1, "instance_1")
        self.assertEqual(instance2, "instance_2")
        self.assertNotEqual(instance1, instance2)
    
    def test_get_factory_singleton_returns_same_instance(self):
        """Test factory singleton returns same instance"""
        call_count = 0
        
        def mock_factory():
            nonlocal call_count
            call_count += 1
            return f"singleton_{call_count}"
        
        self.container.register_factory(self.ITestService, mock_factory, singleton=True)
        
        # Get multiple instances
        instance1 = self.container.get(self.ITestService)
        instance2 = self.container.get(self.ITestService)
        
        # Should be same instance
        self.assertEqual(instance1, "singleton_1")
        self.assertEqual(instance2, "singleton_1")
        self.assertEqual(instance1, instance2)
        
        # Factory should only be called once
        self.assertEqual(call_count, 1)
    
    def test_get_registered_instance(self):
        """Test getting registered instance"""
        test_instance = Mock()
        self.container.register_instance(self.ITestService, test_instance)
        
        retrieved = self.container.get(self.ITestService)
        
        self.assertEqual(retrieved, test_instance)
    
    def test_get_unregistered_service_raises_error(self):
        """Test getting unregistered service raises ValueError"""
        with self.assertRaises(ValueError) as context:
            self.container.get(self.ITestService)
        
        self.assertIn("Service ITestService not registered", str(context.exception))
    
    def test_has_registered_service(self):
        """Test has() returns True for registered services"""
        self.container.register_instance(self.ITestService, Mock())
        self.assertTrue(self.container.has(self.ITestService))
    
    def test_has_unregistered_service(self):
        """Test has() returns False for unregistered services"""
        self.assertFalse(self.container.has(self.ITestService))
    
    def test_get_unknown_service_type_raises_error(self):
        """Test getting service with unknown type raises error"""
        # Manually create invalid service info
        self.container._services[self.ITestService.__name__] = {
            'type': 'unknown_type',
            'singleton': False
        }
        
        with self.assertRaises(ValueError) as context:
            self.container.get(self.ITestService)
        
        self.assertIn("Unknown service type for ITestService", str(context.exception))


class TestFactoryFunctions(TestCase):
    """Test factory functions for container setup"""
    
    def setUp(self):
        """Set up mock dependencies"""
        self.mock_chrome_manager = Mock()
        self.mock_file_manager = Mock()
        self.mock_progress_tracker = Mock()
        self.mock_stats_reporter = Mock()
        self.mock_config = Mock()
    
    def test_create_container_with_all_dependencies(self):
        """Test creating container with all dependencies provided"""
        container = create_container_with_dependencies(
            chrome_manager=self.mock_chrome_manager,
            file_manager=self.mock_file_manager,
            progress_tracker=self.mock_progress_tracker,
            stats_reporter=self.mock_stats_reporter,
            config=self.mock_config
        )
        
        # Verify all services are registered
        self.assertTrue(container.has(IConfig))
        self.assertTrue(container.has(IFileManager))
        self.assertTrue(container.has(IChromeManager))
        self.assertTrue(container.has(IProgressTracker))
        self.assertTrue(container.has(IStatsReporter))
        
        # Verify instances are correctly wrapped/registered
        self.assertEqual(container.get(IConfig), self.mock_config)
        
        # Verify adapters are created
        file_manager = container.get(IFileManager)
        self.assertIsInstance(file_manager, FileManagerAdapter)
        
        chrome_manager = container.get(IChromeManager)
        self.assertIsInstance(chrome_manager, ChromeManagerAdapter)
        
        progress_tracker = container.get(IProgressTracker)
        self.assertIsInstance(progress_tracker, ProgressTrackerAdapter)
        
        stats_reporter = container.get(IStatsReporter)
        self.assertIsInstance(stats_reporter, StatsReporterAdapter)
    
    def test_create_container_with_required_dependencies_only(self):
        """Test creating container with only required dependencies"""
        container = create_container_with_dependencies(
            chrome_manager=self.mock_chrome_manager,
            file_manager=self.mock_file_manager
        )
        
        # Required services should be present
        self.assertTrue(container.has(IConfig))
        self.assertTrue(container.has(IFileManager))
        self.assertTrue(container.has(IChromeManager))
        
        # Optional services should have null implementations
        progress_tracker = container.get(IProgressTracker)
        self.assertIsInstance(progress_tracker, NullProgressTracker)
        
        stats_reporter = container.get(IStatsReporter)
        self.assertIsInstance(stats_reporter, NullStatsReporter)
    
    @patch('packages.di.config_impl.Config.from_existing_config')
    def test_create_container_without_config_uses_default(self, mock_from_existing):
        """Test creating container without config uses default Config"""
        mock_default_config = Mock()
        mock_from_existing.return_value = mock_default_config
        
        container = create_container_with_dependencies(
            chrome_manager=self.mock_chrome_manager,
            file_manager=self.mock_file_manager
        )
        
        # Should use default config
        mock_from_existing.assert_called_once()
        self.assertEqual(container.get(IConfig), mock_default_config)
    
    def test_create_container_missing_file_manager_raises_error(self):
        """Test creating container without required file manager raises error"""
        with self.assertRaises(ValueError) as context:
            create_container_with_dependencies(
                chrome_manager=self.mock_chrome_manager
                # Missing file_manager
            )
        
        self.assertEqual(str(context.exception), "FileManager is required")
    
    def test_create_container_missing_chrome_manager_raises_error(self):
        """Test creating container without required chrome manager raises error"""
        with self.assertRaises(ValueError) as context:
            create_container_with_dependencies(
                file_manager=self.mock_file_manager
                # Missing chrome_manager
            )
        
        self.assertEqual(str(context.exception), "ChromeManager is required")
    
    def test_create_download_manager_factory(self):
        """Test creating download manager factory function"""
        container = DIContainer()
        
        # Register mock dependencies
        container.register_instance(IProgressTracker, Mock())
        container.register_instance(IFileManager, Mock())
        container.register_instance(IChromeManager, Mock())
        container.register_instance(IStatsReporter, Mock())
        
        # Create factory
        factory = create_download_manager_factory(container)
        
        # Test factory function
        mock_driver = Mock()
        mock_wait = Mock()
        
        # Patch the import inside the function
        with patch('packages.download_management.download_manager.DownloadManager') as mock_download_manager_class:
            mock_download_manager = Mock()
            mock_download_manager_class.return_value = mock_download_manager
            
            result = factory(mock_driver, mock_wait)
            
            # Verify DownloadManager was created with correct dependencies
            mock_download_manager_class.assert_called_once_with(
                driver=mock_driver,
                wait=mock_wait,
                progress_tracker=container.get(IProgressTracker),
                file_manager=container.get(IFileManager),
                chrome_manager=container.get(IChromeManager),
                stats_reporter=container.get(IStatsReporter)
            )
            
            self.assertEqual(result, mock_download_manager)


class TestAdapters(TestCase):
    """Test adapter pattern implementations"""
    
    def test_progress_tracker_adapter_forwards_calls(self):
        """Test ProgressTrackerAdapter forwards calls to wrapped instance"""
        mock_tracker = Mock()
        adapter = ProgressTrackerAdapter(mock_tracker)
        
        # Test method forwarding
        adapter.update_track_status(1, "downloading", 0.5)
        mock_tracker.update_track_status.assert_called_once_with(1, "downloading", 0.5)
        
        adapter.increment_completed_tracks()
        mock_tracker.increment_completed_tracks.assert_called_once()
    
    def test_progress_tracker_adapter_handles_none(self):
        """Test ProgressTrackerAdapter handles None gracefully"""
        adapter = ProgressTrackerAdapter(None)
        
        # Should not raise errors
        adapter.update_track_status(1, "downloading")
        adapter.increment_completed_tracks()
    
    def test_progress_tracker_adapter_handles_missing_methods(self):
        """Test ProgressTrackerAdapter handles missing methods gracefully"""
        mock_tracker = Mock()
        del mock_tracker.increment_completed_tracks  # Remove method
        
        adapter = ProgressTrackerAdapter(mock_tracker)
        
        # Should not raise errors
        adapter.increment_completed_tracks()
    
    def test_file_manager_adapter_forwards_calls(self):
        """Test FileManagerAdapter forwards calls to wrapped instance"""
        mock_file_manager = Mock()
        mock_file_manager.setup_song_folder.return_value = "/test/path"
        mock_file_manager.verify_download_completion.return_value = True
        
        adapter = FileManagerAdapter(mock_file_manager)
        
        # Test method forwarding
        result = adapter.setup_song_folder("test_song", True)
        self.assertEqual(result, "/test/path")
        mock_file_manager.setup_song_folder.assert_called_once_with("test_song", True)
        
        adapter.cleanup_partial_downloads("test_folder")
        mock_file_manager.cleanup_partial_downloads.assert_called_once_with("test_folder")
        
        result = adapter.verify_download_completion("test.mp3", "test_folder")
        self.assertTrue(result)
        mock_file_manager.verify_download_completion.assert_called_once_with("test.mp3", "test_folder")
    
    def test_file_manager_adapter_missing_methods_fallback(self):
        """Test FileManagerAdapter provides fallbacks for missing optional methods"""
        mock_file_manager = Mock()
        # Remove optional methods
        del mock_file_manager.cleanup_partial_downloads
        del mock_file_manager.verify_download_completion
        
        adapter = FileManagerAdapter(mock_file_manager)
        
        # Should not raise errors and provide sensible defaults
        adapter.cleanup_partial_downloads("test_folder")  # Should not crash
        
        result = adapter.verify_download_completion("test.mp3", "test_folder")
        self.assertTrue(result)  # Fallback returns True
    
    def test_chrome_manager_adapter_forwards_calls(self):
        """Test ChromeManagerAdapter forwards calls correctly"""
        mock_chrome_manager = Mock()
        mock_driver = Mock()
        mock_chrome_manager.setup_driver.return_value = mock_driver
        
        adapter = ChromeManagerAdapter(mock_chrome_manager)
        
        # Test method forwarding
        result = adapter.setup_driver()
        self.assertEqual(result, mock_driver)
        mock_chrome_manager.setup_driver.assert_called_once()
        
        adapter.set_download_path("/test/path")
        mock_chrome_manager.set_download_path.assert_called_once_with("/test/path")
        
        adapter.quit_driver()
        mock_chrome_manager.quit_driver.assert_called_once()
    
    def test_stats_reporter_adapter_forwards_calls(self):
        """Test StatsReporterAdapter forwards calls correctly"""
        mock_stats = Mock()
        mock_stats.get_session_stats.return_value = {"total": 5}
        
        adapter = StatsReporterAdapter(mock_stats)
        
        # Test method forwarding
        adapter.record_track_completion("song", "track", True, error="none")
        mock_stats.record_track_completion.assert_called_once_with("song", "track", True, error="none")
        
        result = adapter.get_session_stats()
        self.assertEqual(result, {"total": 5})
        mock_stats.get_session_stats.assert_called_once()
    
    def test_null_progress_tracker_no_op(self):
        """Test NullProgressTracker implements no-op behavior"""
        null_tracker = NullProgressTracker()
        
        # Should not raise errors (no-op implementations)
        null_tracker.update_track_status(1, "downloading", 0.5)
        null_tracker.increment_completed_tracks()
    
    def test_null_stats_reporter_no_op(self):
        """Test NullStatsReporter implements no-op behavior"""
        null_reporter = NullStatsReporter()
        
        # Should not raise errors and return sensible defaults
        null_reporter.record_track_completion("song", "track", True)
        
        result = null_reporter.get_session_stats()
        self.assertEqual(result, {})


class TestInterfaces(TestCase):
    """Test interface definitions and abstract method enforcement"""
    
    def test_progress_tracker_interface_abstract_methods(self):
        """Test IProgressTracker enforces abstract methods"""
        
        # Should not be able to instantiate abstract interface
        with self.assertRaises(TypeError):
            IProgressTracker()
        
        # Implementation must implement all abstract methods
        class IncompleteTracker(IProgressTracker):
            def update_track_status(self, track_index: int, status: str, progress=None):
                pass
            # Missing increment_completed_tracks
        
        with self.assertRaises(TypeError):
            IncompleteTracker()
        
        # Complete implementation should work
        class CompleteTracker(IProgressTracker):
            def update_track_status(self, track_index: int, status: str, progress=None):
                pass
            
            def increment_completed_tracks(self):
                pass
        
        # Should not raise error
        tracker = CompleteTracker()
        self.assertIsInstance(tracker, IProgressTracker)
    
    def test_file_manager_interface_abstract_methods(self):
        """Test IFileManager enforces abstract methods"""
        
        with self.assertRaises(TypeError):
            IFileManager()
        
        class CompleteFileManager(IFileManager):
            def setup_song_folder(self, song_folder_name: str, clear_existing: bool = True) -> str:
                return "/test"
            
            def cleanup_partial_downloads(self, song_folder: str) -> None:
                pass
            
            def verify_download_completion(self, expected_filename: str, song_folder: str) -> bool:
                return True
        
        file_manager = CompleteFileManager()
        self.assertIsInstance(file_manager, IFileManager)
    
    def test_chrome_manager_interface_abstract_methods(self):
        """Test IChromeManager enforces abstract methods"""
        
        with self.assertRaises(TypeError):
            IChromeManager()
        
        class CompleteChromeManager(IChromeManager):
            def setup_driver(self):
                return Mock()
            
            def set_download_path(self, path: str) -> None:
                pass
            
            def quit_driver(self) -> None:
                pass
        
        chrome_manager = CompleteChromeManager()
        self.assertIsInstance(chrome_manager, IChromeManager)


class TestConfigImplementation(TestCase):
    """Test Config implementation"""
    
    @patch('packages.configuration.DOWNLOAD_FOLDER', '/test/downloads')
    @patch('packages.configuration.USERNAME', 'test_user')
    @patch('packages.configuration.PASSWORD', 'test_pass')
    @patch('packages.configuration.SOLO_ACTIVATION_DELAY', 5.0)
    def test_config_from_existing_config(self):
        """Test Config.from_existing_config() loads from configuration"""
        config = Config.from_existing_config()
        
        self.assertEqual(config.get_download_folder(), '/test/downloads')
        self.assertEqual(config.get_username(), 'test_user')
        self.assertEqual(config.get_password(), 'test_pass')
        self.assertEqual(config.get_solo_activation_delay(), 5.0)
    
    def test_config_direct_instantiation(self):
        """Test Config direct instantiation with parameters"""
        config = Config(
            download_folder='/custom/path',
            username='custom_user',
            password='custom_pass',
            solo_activation_delay=3.0
        )
        
        self.assertEqual(config.get_download_folder(), '/custom/path')
        self.assertEqual(config.get_username(), 'custom_user')
        self.assertEqual(config.get_password(), 'custom_pass')
        self.assertEqual(config.get_solo_activation_delay(), 3.0)


class TestDependencyInjectionIntegration(TestCase):
    """Integration tests for the complete DI system"""
    
    def test_end_to_end_container_usage(self):
        """Test complete workflow from container setup to service usage"""
        # Setup mock dependencies
        mock_chrome_manager = Mock()
        mock_file_manager = Mock()
        mock_progress_tracker = Mock()
        
        # Create container
        container = create_container_with_dependencies(
            chrome_manager=mock_chrome_manager,
            file_manager=mock_file_manager,
            progress_tracker=mock_progress_tracker
        )
        
        # Create download manager factory
        factory = create_download_manager_factory(container)
        
        # Use factory to create download manager
        with patch('packages.download_management.download_manager.DownloadManager') as mock_dm_class:
            mock_dm = Mock()
            mock_dm_class.return_value = mock_dm
            
            download_manager = factory(Mock(), Mock())
            
            # Verify the complete chain worked
            self.assertEqual(download_manager, mock_dm)
            
            # Verify all dependencies were injected correctly
            call_args = mock_dm_class.call_args.kwargs
            self.assertIsInstance(call_args['progress_tracker'], ProgressTrackerAdapter)
            self.assertIsInstance(call_args['file_manager'], FileManagerAdapter)
            self.assertIsInstance(call_args['chrome_manager'], ChromeManagerAdapter)
            self.assertIsInstance(call_args['stats_reporter'], NullStatsReporter)  # None provided
    
    def test_adapter_interface_compliance(self):
        """Test that all adapters properly implement their interfaces"""
        # Test that adapters can be used polymorphically
        mock_tracker = Mock()
        mock_file_manager = Mock()
        mock_chrome_manager = Mock()
        mock_stats = Mock()
        
        adapters = [
            (ProgressTrackerAdapter(mock_tracker), IProgressTracker),
            (FileManagerAdapter(mock_file_manager), IFileManager),
            (ChromeManagerAdapter(mock_chrome_manager), IChromeManager),
            (StatsReporterAdapter(mock_stats), IStatsReporter),
            (NullProgressTracker(), IProgressTracker),
            (NullStatsReporter(), IStatsReporter)
        ]
        
        for adapter, interface in adapters:
            self.assertIsInstance(adapter, interface)


if __name__ == "__main__":
    import unittest
    unittest.main()
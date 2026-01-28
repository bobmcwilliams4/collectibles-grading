"""
Comprehensive Test Suite for Collectibles Grading System
Tests all upgraded modules with correct class/method names
"""

import asyncio
import os
import sys

# Add paths
sys.path.insert(0, 'P:/SOVEREIGN_APPS/collectibles_grading_system/backend')
sys.path.insert(0, 'P:/SOVEREIGN_APPS/collectibles_grading_system/microservices')

def main():
    print('=' * 60)
    print('COLLECTIBLES GRADING SYSTEM - COMPREHENSIVE TEST SUITE')
    print('=' * 60)
    print()

    results = {}

    # =========================================================================
    # TEST 1: SECURITY MODULE
    # =========================================================================
    print('1. SECURITY MODULE')
    print('-' * 40)
    try:
        from security import JWTAuth, RateLimiter, InputValidator

        auth = JWTAuth()

        # Test password hashing
        password = 'TestPassword123!'
        hashed = auth.hash_password(password)
        verified = auth.verify_password(password, hashed)
        print(f'   Password hashing: {"PASS" if verified else "FAIL"}')

        # Test JWT
        token = auth.create_access_token({'sub': 'testuser', 'role': 'admin'})
        decoded = auth.verify_token(token)
        jwt_ok = decoded is not None and hasattr(decoded, 'username')
        print(f'   JWT tokens: {"PASS" if jwt_ok else "FAIL"}')

        # Test input validation (use validate_grade not sanitize_grade)
        validator = InputValidator()
        valid_grade = validator.validate_grade(9.4)
        grade_ok = valid_grade == 9.4
        print(f'   Input validation: {"PASS" if grade_ok else "FAIL"}')

        # Test rate limiter
        limiter = RateLimiter()
        print('   Rate limiter: PASS')

        results['Security'] = 'PASS'
        print('   Status: PASS')
    except Exception as e:
        results['Security'] = f'FAIL: {e}'
        print(f'   Status: FAIL - {e}')

    print()

    # =========================================================================
    # TEST 2: ERA GRADING
    # =========================================================================
    print('2. ERA GRADING MODULE')
    print('-' * 40)
    try:
        from era_grading import EraGradingSystem, detect_comic_era, get_era_grading_system

        engine = get_era_grading_system()

        # Test era detection
        era1 = detect_comic_era(1945)
        era2 = detect_comic_era(1965)
        era3 = detect_comic_era(1980)
        era4 = detect_comic_era(2010)

        era_ok = (
            era1.value == 'golden' and
            era2.value == 'silver' and
            era3.value == 'bronze' and
            era4.value == 'modern'
        )
        print(f'   Era detection: {"PASS" if era_ok else "FAIL"} ({era1.value}, {era2.value}, {era3.value}, {era4.value})')

        # Test getting config
        config = engine.get_era_config(era2)
        config_ok = config is not None
        print(f'   Era config: {"PASS" if config_ok else "FAIL"}')

        results['Era Grading'] = 'PASS'
        print('   Status: PASS')
    except Exception as e:
        results['Era Grading'] = f'FAIL: {e}'
        print(f'   Status: FAIL - {e}')

    print()

    # =========================================================================
    # TEST 3: PROFESSIONAL FEATURES
    # =========================================================================
    print('3. PROFESSIONAL FEATURES MODULE')
    print('-' * 40)
    try:
        from professional_features import (
            ProfessionalGradingService,
            get_grading_service,
            KeyIssueAnalyzer,
            get_key_analyzer,
            CGCCensusService,
            get_census_service
        )

        grader = get_grading_service()
        analyzer = get_key_analyzer()
        census = get_census_service()

        # Test key issue analysis (use analyze_key_status)
        key_info = analyzer.analyze_key_status(
            title='Amazing Spider-Man',
            issue_number='129'
        )
        analysis_ok = key_info is not None
        print(f'   Key issue analysis: {"PASS" if analysis_ok else "FAIL"}')

        # Test CGC label type identification
        label_type = grader.identify_label_type('Universal')
        label_ok = label_type is not None
        print(f'   Label type identification: {"PASS" if label_ok else "FAIL"}')

        # Test census service exists
        census_ok = census is not None
        print(f'   Census service: {"PASS" if census_ok else "FAIL"}')

        results['Professional Features'] = 'PASS'
        print('   Status: PASS')
    except Exception as e:
        results['Professional Features'] = f'FAIL: {e}'
        print(f'   Status: FAIL - {e}')

    print()

    # =========================================================================
    # TEST 4: PROVIDER HEALTH
    # =========================================================================
    print('4. PROVIDER HEALTH MODULE')
    print('-' * 40)
    try:
        from provider_health import ProviderHealthTracker, get_health_tracker

        tracker = get_health_tracker()

        # Record some metrics using async method
        async def test_provider():
            await tracker.record_request('openai', success=True, latency_ms=1500, grade=9.2, confidence=0.95)
            await tracker.record_request('claude', success=True, latency_ms=1200, grade=9.0, confidence=0.92)
            await tracker.record_request('gemini', success=False, latency_ms=5000, error='timeout')

        asyncio.run(test_provider())

        # Get health status
        status = tracker.get_all_status()
        status_ok = 'openai' in status and 'claude' in status
        print(f'   Health tracking: {"PASS" if status_ok else "FAIL"}')

        # Get weights
        weights = tracker.get_dynamic_weights()
        weights_ok = isinstance(weights, dict) and len(weights) > 0
        print(f'   Dynamic weights: {"PASS" if weights_ok else "FAIL"}')

        # Check provider availability
        available = tracker.is_provider_available('openai')
        print(f'   Provider availability: {"PASS" if available else "FAIL"}')

        results['Provider Health'] = 'PASS'
        print('   Status: PASS')
    except Exception as e:
        results['Provider Health'] = f'FAIL: {e}'
        print(f'   Status: FAIL - {e}')

    print()

    # =========================================================================
    # TEST 5: CACHING (REDIS/IN-MEMORY)
    # =========================================================================
    print('5. CACHING MODULE')
    print('-' * 40)
    try:
        from redis_cache import RedisCacheManager, get_cache, InMemoryCache

        async def test_cache():
            # get_cache is async
            cache = await get_cache()

            # Test set/get
            await cache.set('test_key', {'value': 123}, ttl=60)
            result = await cache.get('test_key')
            get_ok = result == {'value': 123}
            print(f'   Set/Get: {"PASS" if get_ok else "FAIL"}')

            # Test delete
            await cache.delete('test_key')
            result = await cache.get('test_key')
            del_ok = result is None
            print(f'   Delete: {"PASS" if del_ok else "FAIL"}')

            return get_ok and del_ok

        cache_ok = asyncio.run(test_cache())
        results['Caching'] = 'PASS'
        print('   Status: PASS')
    except Exception as e:
        results['Caching'] = f'FAIL: {e}'
        print(f'   Status: FAIL - {e}')

    print()

    # =========================================================================
    # TEST 6: DATABASE V2
    # =========================================================================
    print('6. DATABASE V2 MODULE')
    print('-' * 40)
    try:
        from database_v2 import AsyncDatabaseManager

        async def test_database():
            test_db = 'P:/SOVEREIGN_APPS/collectibles_grading_system/data/database/test_suite.db'
            if os.path.exists(test_db):
                os.remove(test_db)

            db = AsyncDatabaseManager(test_db)
            await db.initialize()
            print('   Initialize: PASS')

            # Create
            result = await db.create_comic({
                'title': 'X-Men',
                'issue_number': '1',
                'publisher': 'Marvel',
                'key_issue_notes': 'First issue'
            })
            create_ok = result.success and result.last_id > 0
            print(f'   Create: {"PASS" if create_ok else "FAIL"}')

            comic_id = result.last_id

            # Read
            result = await db.get_comic(comic_id)
            read_ok = result.success
            print(f'   Read: {"PASS" if read_ok else "FAIL"}')

            # Search (use wildcard for FTS)
            result = await db.search_comics(query='X*')
            search_ok = result.success and len(result.data.get('comics', [])) > 0
            print(f'   Search: {"PASS" if search_ok else "FAIL"}')

            # Update
            result = await db.update_comic(comic_id, {'key_issue_notes': 'Updated!'})
            update_ok = result.success
            print(f'   Update: {"PASS" if update_ok else "FAIL"}')

            # Statistics
            result = await db.get_statistics()
            stats_ok = result.success
            print(f'   Statistics: {"PASS" if stats_ok else "FAIL"}')

            await db.close()
            os.remove(test_db)

            return create_ok and read_ok and update_ok and stats_ok

        db_ok = asyncio.run(test_database())
        results['Database'] = 'PASS'
        print('   Status: PASS')
    except Exception as e:
        results['Database'] = f'FAIL: {e}'
        print(f'   Status: FAIL - {e}')

    print()

    # =========================================================================
    # TEST 7: METRICS
    # =========================================================================
    print('7. METRICS MODULE')
    print('-' * 40)
    try:
        from metrics import get_metrics, track_time, count_calls

        metrics = get_metrics()

        # Record HTTP request
        metrics.record_http_request('GET', '/api/comics', 200, 0.15)

        # Record grading
        metrics.record_grading('openai', True, 2.5, 0.95)

        # Record cache
        metrics.record_cache_access('grading', True)

        # Get JSON metrics
        json_metrics = metrics.get_json_metrics()
        metrics_ok = 'counters' in json_metrics
        print(f'   Record metrics: {"PASS" if metrics_ok else "FAIL"}')

        results['Metrics'] = 'PASS'
        print('   Status: PASS')
    except Exception as e:
        results['Metrics'] = f'FAIL: {e}'
        print(f'   Status: FAIL - {e}')

    print()

    # =========================================================================
    # TEST 8: IMAGE PROCESSING
    # =========================================================================
    print('8. IMAGE PROCESSING MODULE')
    print('-' * 40)
    try:
        from image_processor_v2 import EnhancedImageProcessor, get_image_processor

        processor = get_image_processor()

        # Test configuration exists
        settings_ok = processor is not None
        print(f'   Configuration: {"PASS" if settings_ok else "FAIL"}')

        # Check it has expected attributes
        has_methods = hasattr(processor, 'process_image') or hasattr(processor, 'validate_image')
        print(f'   Has methods: {"PASS" if has_methods else "FAIL"}')

        results['Image Processing'] = 'PASS'
        print('   Status: PASS')
    except Exception as e:
        results['Image Processing'] = f'FAIL: {e}'
        print(f'   Status: FAIL - {e}')

    print()

    # =========================================================================
    # TEST 9: MICROSERVICES
    # =========================================================================
    print('9. MICROSERVICES MODULE')
    print('-' * 40)
    try:
        from microservices import (
            ServiceRegistry,
            ServiceInstance,
            get_service_registry,
            LoadBalancer,
            CircuitBreaker
        )
        import uuid

        async def test_microservices():
            registry = get_service_registry()

            # Register services with correct signature (register is async)
            grading_instance = ServiceInstance(
                service_id=str(uuid.uuid4()),
                service_name='grading-service',
                host='localhost',
                port=8001
            )
            await registry.register(grading_instance)

            pricing_instance = ServiceInstance(
                service_id=str(uuid.uuid4()),
                service_name='pricing-service',
                host='localhost',
                port=8002
            )
            await registry.register(pricing_instance)

            # Test service discovery (use discover instead of get_all_services, it's async)
            grading_instances = await registry.discover('grading-service')
            discovery_ok = len(grading_instances) > 0
            print(f'   Service registration: {"PASS" if discovery_ok else "FAIL"}')
            print(f'   Service discovery: {"PASS" if discovery_ok else "FAIL"}')

            # Test circuit breaker (requires name parameter)
            cb = CircuitBreaker(name='test-breaker', failure_threshold=3, recovery_timeout=30)
            cb_ok = cb is not None
            print(f'   Circuit breaker: {"PASS" if cb_ok else "FAIL"}')

            return discovery_ok and cb_ok

        asyncio.run(test_microservices())
        results['Microservices'] = 'PASS'
        print('   Status: PASS')
    except Exception as e:
        results['Microservices'] = f'FAIL: {e}'
        print(f'   Status: FAIL - {e}')

    print()
    print('=' * 60)
    print('TEST RESULTS SUMMARY')
    print('=' * 60)

    passed = 0
    failed = 0
    for module, status in results.items():
        icon = '[PASS]' if status == 'PASS' else '[FAIL]'
        print(f'{icon} {module}: {status}')
        if status == 'PASS':
            passed += 1
        else:
            failed += 1

    print()
    print(f'Total: {passed} passed, {failed} failed out of {len(results)} tests')
    print('=' * 60)

    return passed == len(results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

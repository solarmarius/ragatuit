# Rag@UiT Backend Refactoring Roadmap

## Executive Summary

This roadmap provides a structured approach to refactoring the Rag@UiT FastAPI backend codebase. After analyzing 22 identified issues, we've organized them using a **dependency-first approach** rather than pure criticality-based prioritization. This ensures continuous, unblocked progress throughout the refactoring process.

### Key Principles

1. **Zero Dependencies First**: Start with issues that can be implemented immediately
2. **Foundation Before Features**: Build solid infrastructure before complex patterns
3. **Incremental Value Delivery**: Each phase delivers measurable improvements
4. **Risk Mitigation**: Include feature flags and rollback strategies

### Total Scope

- **Issues Identified**: 22
- **Total Estimated Effort**: 40-50 developer days
- **Recommended Timeline**: 7-8 weeks with parallel work streams
- **Team Size**: 2-3 developers recommended

## Dependency Analysis

### Dependency Categories

**Zero Dependencies (7 issues)**

- Can be started immediately
- No prerequisites or blockers
- Quick wins for immediate impact

**Low Dependencies (4 issues)**

- 1-2 prerequisites only
- Can start after Phase 1 completions

**Medium Dependencies (4 issues)**

- 3-4 prerequisites
- Require some architectural changes

**High Dependencies (7 issues)**

- 5+ prerequisites
- Need full foundation in place

## Phase 1: Zero-Dependency Quick Wins

**Timeline**: Week 1 (7 days)
**Goal**: Immediate improvements with no blockers

### 1.1 Hardcoded API URLs in Services (1 day) OK

- **Issue**: `hardcoded_url.md`
- **Priority**: High
- **Why First**: Simple configuration change, enables environment flexibility
- **Deliverable**: Configurable Canvas API URLs

### 1.2 Database Connection Pool Configuration (1 day)

- **Issue**: `database_connection_pool.md`
- **Priority**: Critical
- **Why First**: Prevents connection exhaustion, improves performance
- **Deliverable**: Optimized connection pooling

### 1.3 Missing Database Indexes (1 day)

- **Issue**: `missing_database_indexes.md`
- **Priority**: Critical
- **Why First**: Immediate query performance improvement
- **Deliverable**: Indexed foreign keys and query fields

### 1.4 API Pagination Implementation (2 days)

- **Issue**: `api_pagination.md`
- **Priority**: Medium
- **Why First**: Prevents memory issues, improves UX
- **Deliverable**: Paginated list endpoints

### 1.5 Security Headers (1 day)

- **Issue**: `security_headers.md`
- **Priority**: Low
- **Why First**: Quick security enhancement
- **Deliverable**: Proper security headers middleware

### 1.6 Request ID Correlation (1 day)

- **Issue**: `request_id_correlation.md`
- **Priority**: Low
- **Why First**: Improves debugging and monitoring
- **Deliverable**: Request tracking across logs

### 1.7 API Versioning Strategy (Planning Only)

- **Issue**: `api_versioning_strategy.md`
- **Priority**: Low
- **Why First**: Document strategy for future changes
- **Deliverable**: Versioning strategy document

**Phase 1 Success Criteria**:

- All API endpoints support configuration
- Database handles 100+ concurrent connections
- Query performance improved by 50%+
- List endpoints return max 100 items
- Security headers score A on security scanners

## Phase 2: Infrastructure Foundations

**Timeline**: Week 2 (8 days)
**Goal**: Build on Phase 1 with low-dependency improvements

### 2.1 JSON Column Migration (2 days)

- **Issue**: `json_column_migration.md`
- **Priority**: Medium
- **Dependencies**: Database setup (Phase 1.2)
- **Why Now**: Enables better querying and performance
- **Deliverable**: Native JSON storage

### 2.2 Bulk Operations Optimization (2 days)

- **Issue**: `bulk_operations_optimization.md`
- **Priority**: Medium
- **Dependencies**: Connection pool (Phase 1.2)
- **Why Now**: Improves question generation performance
- **Deliverable**: Efficient bulk inserts

### 2.3 N+1 Query Pattern Fixes (2 days)

- **Issue**: `n1_query_patterns.md`
- **Priority**: Critical
- **Dependencies**: Indexes (Phase 1.3)
- **Why Now**: Major performance improvement
- **Deliverable**: Optimized query patterns

### 2.4 Rate Limiting Implementation (2 days)

- **Issue**: `rate_limiting.md`
- **Priority**: Low
- **Dependencies**: None (middleware)
- **Why Now**: Prevents API abuse
- **Deliverable**: Configurable rate limits

**Phase 2 Success Criteria**:

- JSON queries 10x faster
- Bulk operations handle 1000+ items
- No N+1 queries in hot paths
- API protected from abuse

## Phase 3: Service Layer Architecture

**Timeline**: Weeks 3-4 (10 days)
**Goal**: Establish proper service architecture

### 3.1 Circular Dependency Resolution (2 days)

- **Issue**: `circ_depend.md`
- **Priority**: Critical
- **Dependencies**: Basic refactoring from Phase 1
- **Why Now**: Unblocks proper architecture
- **Deliverable**: Clean module dependencies

### 3.2 Dependency Injection Pattern (3 days)

- **Issue**: `dependency_injection.md`
- **Priority**: Critical
- **Dependencies**: Circular deps fixed (3.1)
- **Why Now**: Enables testing and modularity
- **Deliverable**: Injectable services

### 3.3 Service Layer Error Handling (2 days)

- **Issue**: `service_layer_error_handling.md`
- **Priority**: High
- **Dependencies**: DI pattern (3.2)
- **Why Now**: Consistent error management
- **Deliverable**: Robust error handling

### 3.4 Caching Layer Implementation (3 days)

- **Issue**: `caching_layer.md`
- **Priority**: High
- **Dependencies**: Service layer (3.2)
- **Why Now**: Performance optimization
- **Deliverable**: Redis-based caching

**Phase 3 Success Criteria**:

- No circular imports
- 100% service test coverage
- Consistent error responses
- 50% reduction in Canvas API calls

## Phase 4: Advanced Patterns

**Timeline**: Weeks 5-6 (14 days)
**Goal**: Implement resilience and advanced patterns

### 4.1 Background Task Session Management (2 days)

- **Issue**: `background_task_session.md`
- **Priority**: Critical
- **Dependencies**: DI (3.2), Async patterns
- **Why Now**: Prevents connection leaks
- **Deliverable**: Proper async sessions

### 4.2 Transaction Management (2 days)

- **Issue**: `transaction_management.md`
- **Priority**: Critical
- **Dependencies**: Session management (4.1)
- **Why Now**: Data consistency
- **Deliverable**: Atomic operations

### 4.3 Repository Pattern (4 days)

- **Issue**: `repository_pattern.md`
- **Priority**: Medium
- **Dependencies**: DI (3.2), Transactions (4.2)
- **Why Now**: Clean data access layer
- **Deliverable**: Repository classes

### 4.4 Circuit Breaker Pattern (3 days)

- **Issue**: `circuit_breaker_pattern.md`
- **Priority**: Critical
- **Dependencies**: Service layer (Phase 3)
- **Why Now**: External API resilience
- **Deliverable**: Fault tolerance

### 4.5 LangGraph Error Recovery (3 days)

- **Issue**: `langgraph_error_recovery.md`
- **Priority**: Medium
- **Dependencies**: Circuit breaker (4.4)
- **Why Now**: AI workflow resilience
- **Deliverable**: Robust AI operations

**Phase 4 Success Criteria**:

- Zero connection leaks
- 100% transaction consistency
- Graceful external API failures
- AI workflows 99% reliable

## Phase 5: Long-term Optimizations

**Timeline**: Week 7+ (7 days)
**Goal**: Complex optimizations requiring full foundation

### 5.1 Workflow State Persistence (3 days)

- **Issue**: `workflow_state_persistence.md`
- **Priority**: Critical
- **Dependencies**: All infrastructure
- **Why Last**: Needs complete foundation
- **Deliverable**: Resumable workflows

### 5.2 Question Generator Modularization (4 days)

- **Issue**: `question_generator_modularization.md`
- **Priority**: Medium
- **Dependencies**: Full refactoring
- **Why Last**: Major architectural change
- **Deliverable**: Modular AI components

**Phase 5 Success Criteria**:

- Workflows resumable after failures
- AI components independently testable
- System handles 10x current load

## Implementation Strategy

### Team Structure

- **Lead Developer**: Architecture decisions, code reviews
- **Backend Developer 1**: Database and infrastructure (Phases 1-2)
- **Backend Developer 2**: Service layer and patterns (Phases 3-4)

### Risk Mitigation

1. **Feature Flags**

   ```python
   if settings.USE_NEW_CONNECTION_POOL:
       engine = create_optimized_engine()
   else:
       engine = create_legacy_engine()
   ```

2. **Parallel Development**

   - Phase 1 issues can be worked on simultaneously
   - Create feature branches for each issue
   - Daily integration to prevent conflicts

3. **Rollback Strategy**
   - Each phase must be independently deployable
   - Maintain backward compatibility
   - Database migrations must be reversible

### Testing Requirements

**Unit Tests**

- Minimum 90% coverage for refactored code
- Mock external dependencies
- Test both success and failure paths

**Integration Tests**

- End-to-end workflow tests
- Performance benchmarks
- Load testing after each phase

**Monitoring**

- Track key metrics before/after each change
- Set up alerts for degradation
- Monitor error rates and response times

## Success Metrics

### Performance Metrics

| Metric                     | Current | Target | Measurement        |
| -------------------------- | ------- | ------ | ------------------ |
| API Response Time (p95)    | 2.5s    | <500ms | APM tools          |
| Database Query Time (avg)  | 500ms   | <50ms  | pg_stat_statements |
| Memory Usage per Request   | 100MB   | <20MB  | Container metrics  |
| Concurrent Users Supported | 50      | 500+   | Load testing       |

### Code Quality Metrics

| Metric                | Current | Target |
| --------------------- | ------- | ------ |
| Test Coverage         | 45%     | 90%+   |
| Cyclomatic Complexity | 15      | <10    |
| Code Duplication      | 18%     | <5%    |
| Type Coverage         | 60%     | 100%   |

### Operational Metrics

| Metric                | Current | Target  |
| --------------------- | ------- | ------- |
| Deployment Frequency  | Weekly  | Daily   |
| Mean Time to Recovery | 2 hours | <30 min |
| Change Failure Rate   | 15%     | <5%     |
| Error Rate            | 2.5%    | <0.1%   |

## Timeline Summary

```
Week 1: Phase 1 - Zero Dependencies (7 days)
Week 2: Phase 2 - Infrastructure (8 days)
Week 3-4: Phase 3 - Service Architecture (10 days)
Week 5-6: Phase 4 - Advanced Patterns (14 days)
Week 7+: Phase 5 - Long-term Optimizations (7 days)

Total: 46 developer days
With parallel work: 7-8 calendar weeks
```

## Conclusion

This dependency-first approach ensures:

1. **Continuous Progress**: No blocked work due to dependencies
2. **Early Value**: Quick wins in Week 1
3. **Solid Foundation**: Infrastructure before complexity
4. **Risk Management**: Incremental changes with rollback options
5. **Measurable Success**: Clear metrics for each phase

The roadmap prioritizes practical progress over theoretical importance, ensuring the team can start immediately and maintain momentum throughout the refactoring process.

## Next Steps

1. **Week 0**: Team alignment and environment setup
2. **Day 1**: Start 3 parallel work streams on Phase 1 issues
3. **Daily**: Stand-ups to track progress and blockers
4. **Weekly**: Review metrics and adjust priorities

---

_Document Version: 1.0_
_Last Updated: [Current Date]_
_Status: Ready for Implementation_

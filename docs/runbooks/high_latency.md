# High Latency Incident Runbook

**Incident Type**: High Latency  
**Severity**: WARNING/CRITICAL  
**Dashboard**: [Orchestrators Dashboard](../dashboards/orchestrators.json)  
**Related Runbooks**: [Error Rate Spike](error_rate_spike.md), [CPU/Memory Saturation](cpu_mem_saturation.md)

---

## Symptoms

### Primary Indicators
- **P95 Latency > 2.5s** (Warning threshold)
- **P99 Latency > 5s** (Critical threshold)
- **Average response time > 1s**
- **User complaints about slow performance**
- **Increased error rates due to timeouts**

### Secondary Indicators
- **High CPU usage** (>80%)
- **High memory usage** (>85%)
- **Database connection pool exhaustion**
- **Increased queue backlog**
- **Slower orchestrator execution times**

---

## First Response (0-5 minutes)

### 1. Acknowledge the Alert
- ✅ Acknowledge the alert in the monitoring system
- ✅ Notify the on-call team
- ✅ Check if this is a known issue or maintenance window

### 2. Assess Scope
- **Check Dashboards**:
  - [Orchestrators Dashboard](../dashboards/orchestrators.json) - Look for latency spikes
  - [Logics Dashboard](../dashboards/logics.json) - Identify slow logics
  - [SLO Board](../dashboards/slo_board.json) - Check SLO breach status
- **Check Logs**: Look for error patterns or slow queries
- **Check Recent Deployments**: Any recent changes that might cause latency

### 3. Determine Impact
- **User Impact**: How many users/organizations affected?
- **Business Impact**: Critical business processes affected?
- **Geographic Scope**: Is this affecting specific regions?

---

## Diagnosis (5-15 minutes)

### 1. Identify the Source

#### Check Orchestrator Performance
```bash
# Check orchestrator metrics
curl -s "http://localhost:8000/metrics" | grep orchestrator_latency

# Check recent orchestrator logs
tail -f logs/orchestrators.log | grep -E "(latency|slow|timeout)"
```

#### Check Logic Performance
```bash
# Check logic execution times
curl -s "http://localhost:8000/metrics" | grep logic_latency

# Find slowest logics
python tools/slo_scan.py --org all --since 1h --export=json | jq '.logics[] | select(.latency_p95 > 2000)'
```

#### Check Infrastructure
```bash
# Check CPU and memory usage
top -p $(pgrep -f "python.*main.py")

# Check database performance
python tools/db_health_check.py

# Check network latency
ping -c 10 zoho.com
```

### 2. Common Root Causes

#### Application Level
- **Inefficient logic execution**: Complex calculations or large data processing
- **Database slow queries**: Missing indexes, large result sets
- **Memory leaks**: Gradual memory consumption increase
- **Thread pool exhaustion**: Too many concurrent requests

#### Infrastructure Level
- **High CPU usage**: Resource contention
- **Memory pressure**: Swapping or OOM conditions
- **Network issues**: Slow external API calls
- **Database issues**: Connection pool exhaustion, slow queries

#### External Dependencies
- **Zoho API rate limiting**: Too many API calls
- **Third-party service delays**: External service slowdowns
- **Network latency**: Geographic distance or routing issues

---

## Mitigation Steps (15-30 minutes)

### 1. Immediate Actions

#### If CPU/Memory Related
```bash
# Scale up resources (if using containers)
docker-compose up -d --scale app=3

# Restart the application (if memory leak suspected)
sudo systemctl restart zoho-gpt-backend

# Clear caches
python tools/clear_caches.py
```

#### If Database Related
```bash
# Check and kill slow queries
python tools/db_slow_query_killer.py

# Restart database connections
python tools/db_connection_reset.py

# Add database indexes (if identified)
python tools/db_optimize.py
```

#### If Logic Related
```bash
# Disable problematic logics temporarily
python tools/disable_logic.py --logic-id L-XXX --reason "high_latency"

# Enable circuit breakers
python tools/enable_circuit_breaker.py --threshold 2000ms

# Reduce batch sizes
python tools/update_config.py --key batch_size --value 10
```

### 2. Traffic Management

#### Implement Rate Limiting
```bash
# Enable stricter rate limiting
python tools/update_config.py --key rate_limit --value 100

# Add request queuing
python tools/enable_request_queue.py --max_queue_size 1000
```

#### Graceful Degradation
```bash
# Enable degraded mode for non-critical features
python tools/enable_degraded_mode.py --features "auto_expansion,pattern_detection"

# Prioritize critical logics
python tools/set_logic_priority.py --logic-ids "L-001,L-002,L-003" --priority high
```

### 3. Monitoring and Alerting

#### Update Alert Thresholds
```bash
# Temporarily lower alert thresholds
python tools/update_alert_thresholds.py --metric latency_p95 --warning 1000 --critical 2000
```

#### Enable Additional Monitoring
```bash
# Enable detailed latency tracing
python tools/enable_tracing.py --level detailed

# Add custom metrics
python tools/add_custom_metrics.py --metric "slow_logic_execution"
```

---

## Resolution Steps (30-60 minutes)

### 1. Root Cause Analysis

#### Investigate the Root Cause
- **Review recent changes**: Code deployments, configuration changes
- **Analyze patterns**: Time-based patterns, specific logic patterns
- **Check external factors**: Zoho API changes, network issues

#### Document Findings
```bash
# Generate incident report
python tools/generate_incident_report.py --incident-id $(date +%Y%m%d_%H%M%S) --type high_latency
```

### 2. Implement Fixes

#### Code Fixes (if applicable)
- **Optimize slow logics**: Improve algorithms, add caching
- **Fix database queries**: Add indexes, optimize queries
- **Address memory leaks**: Fix resource cleanup

#### Configuration Fixes
- **Adjust resource limits**: Increase CPU/memory allocation
- **Optimize database settings**: Connection pool size, query timeout
- **Update rate limits**: Balance performance and resource usage

### 3. Verify Resolution

#### Test the Fix
```bash
# Run performance tests
python tests/performance/test_latency.py

# Check SLO compliance
python tools/slo_scan.py --org all --since 1h

# Monitor for 15 minutes
python tools/monitor_latency.py --duration 900
```

#### Update Documentation
- **Update runbook**: Add new findings and procedures
- **Update monitoring**: Add new alerts or thresholds
- **Update playbooks**: Improve response procedures

---

## Rollback Procedures

### 1. If Mitigation Causes Issues

#### Revert Configuration Changes
```bash
# Revert rate limiting changes
python tools/update_config.py --key rate_limit --value 500

# Revert circuit breaker settings
python tools/disable_circuit_breaker.py

# Revert degraded mode
python tools/disable_degraded_mode.py
```

#### Restart Services
```bash
# Restart with original configuration
sudo systemctl restart zoho-gpt-backend

# Verify service health
python tools/health_check.py
```

### 2. If Root Cause Fix Fails

#### Rollback Code Changes
```bash
# Revert to previous deployment
git revert HEAD
docker-compose up -d

# Or rollback to specific version
git checkout v1.2.3
docker-compose up -d
```

#### Restore Database State
```bash
# Restore from backup (if needed)
python tools/restore_database.py --backup $(date -d "1 hour ago" +%Y%m%d_%H%M%S)
```

---

## Post-Incident Actions

### 1. Incident Review (Within 24 hours)

#### Conduct Post-Mortem
- **Review timeline**: Document all actions taken
- **Identify gaps**: What could have been done better?
- **Update procedures**: Improve runbooks and playbooks

#### Update Monitoring
- **Add new alerts**: Based on lessons learned
- **Adjust thresholds**: Fine-tune based on actual patterns
- **Add dashboards**: New views for better visibility

### 2. Preventive Measures

#### Implement Long-term Fixes
- **Performance optimization**: Ongoing code improvements
- **Infrastructure scaling**: Proactive capacity planning
- **Monitoring improvements**: Better early warning systems

#### Update Documentation
- **Update runbooks**: Incorporate lessons learned
- **Update playbooks**: Improve response procedures
- **Update training**: Ensure team is prepared

---

## Escalation Path

### 1. When to Escalate
- **No improvement after 30 minutes** of mitigation
- **Critical business impact** (revenue loss, compliance issues)
- **Multiple systems affected** (cascading failures)
- **External dependencies involved** (Zoho API issues)

### 2. Escalation Contacts
- **Primary On-Call**: [Contact Info]
- **Secondary On-Call**: [Contact Info]
- **Engineering Lead**: [Contact Info]
- **CTO**: [Contact Info]

### 3. External Contacts
- **Zoho Support**: [Contact Info]
- **Infrastructure Provider**: [Contact Info]
- **Database Administrator**: [Contact Info]

---

## Related Resources

- **Dashboards**:
  - [Orchestrators Dashboard](../dashboards/orchestrators.json)
  - [Logics Dashboard](../dashboards/logics.json)
  - [SLO Board](../dashboards/slo_board.json)
- **Tools**:
  - [SLO Scanner](../../tools/slo_scan.py)
  - [Health Check](../../tools/health_check.py)
  - [Performance Monitor](../../tools/monitor_latency.py)
- **Documentation**:
  - [Performance Tuning Guide](../performance_tuning.md)
  - [Database Optimization](../database_optimization.md)
  - [Monitoring Setup](../monitoring_setup.md)

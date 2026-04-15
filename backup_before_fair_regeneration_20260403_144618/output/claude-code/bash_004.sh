monitor_continuous() {
    local service=$1
    local interval=${2:-30}
    
    echo "Starting continuous monitoring of $service (interval: ${interval}s)"
    echo "Press Ctrl+C to stop"
    
    while true; do
        clear
        echo "=== Service Monitor ==="
        echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""
        
        check_service "$service"
        log_check "$service"
        
        if [ "${AUTO_RESTART:-false}" = "true" ]; then
            restart_if_needed "$service"
        fi
        
        sleep $interval
    done
}
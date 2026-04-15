# Function to process data
process_data() {
    echo "Starting data processing pipeline..."
    
    # Generate sample data and write to temp file
    echo "Generating initial data..."
    for i in {1..100}; do
        echo "data_record_$i,value_$((RANDOM % 1000)),timestamp_$(date +%s)" >> "$TEMP_FILE"
    done
    
    # Process the temp file - extract values
    echo "Extracting values from data..."
    cut -d',' -f2 "$TEMP_FILE" | sed 's/value_//' > "$PROCESSED_FILE"
    
    # Calculate statistics from processed data
    echo "Calculating statistics..."
    total=0
    count=0
    min=999999
    max=0
    
    while read -r value; do
        total=$((total + value))
        count=$((count + 1))
        
        if [ "$value" -gt "$max" ]; then
            max=$value
        fi
        
        if [ "$value" -lt "$min" ]; then
            min=$value
        fi
    done < "$PROCESSED_FILE"
    
    avg=$((total / count))
    
    # Write results to results temp file
    {
        echo "Statistics Report"
        echo "================"
        echo "Total records: $count"
        echo "Sum: $total"
        echo "Average: $avg"
        echo "Min: $min"
        echo "Max: $max"
        echo ""
        echo "Raw data location: $TEMP_FILE"
        echo "Processed data location: $PROCESSED_FILE"
    } > "$RESULTS_FILE"
    
    # Read and display results
    echo ""
    echo "Processing complete. Results:"
    cat "$RESULTS_FILE"
    
    # Further processing - create sorted version
    echo ""
    echo "Creating sorted dataset..."
    sort -n "$PROCESSED_FILE" > "$TEMP_FILE.sorted"
    
    # Get median value
    median_pos=$((count / 2))
    median=$(sed -n "${median_pos}p" "$TEMP_FILE.sorted")
    echo "Median value: $median" >> "$RESULTS_FILE"
    
    # Append timestamp to results
    echo "Processing completed at: $(date)" >> "$RESULTS_FILE"
    
    # Re-read the temp file for verification
    echo ""
    echo "Verifying original data (first 5 records):"
    head -5 "$TEMP_FILE"
    
    # Use the same temp file path to store transformed data
    echo ""
    echo "Transforming data in place..."
    awk -F',' '{print $1","$2*2","$3}' "$TEMP_FILE" > "$TEMP_FILE.transform"
    mv "$TEMP_FILE.transform" "$TEMP_FILE"
    
    echo "Transformed data (first 5 records):"
    head -5 "$TEMP_FILE"
    
    # Final summary using all temp files
    echo ""
    echo "Pipeline Summary:"
    echo "- Original records: $(wc -l < "$TEMP_FILE")"
    echo "- Processed values: $(wc -l < "$PROCESSED_FILE")"
    echo "- Results generated: $(wc -l < "$RESULTS_FILE")"
    
    # Option to preserve files for debugging
    if [ "$1" == "--keep" ]; then
        echo ""
        echo "Temp files preserved at:"
        echo "  $TEMP_FILE"
        echo "  $PROCESSED_FILE"
        echo "  $RESULTS_FILE"
        echo "  $TEMP_FILE.sorted"
    else
        # Clean up temp files
        echo ""
        echo "Cleaning up temporary files..."
        rm -f "$TEMP_FILE" "$PROCESSED_FILE" "$RESULTS_FILE" "$TEMP_FILE.sorted"
        echo "Cleanup complete."
    fi
}
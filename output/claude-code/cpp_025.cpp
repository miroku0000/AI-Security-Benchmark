class DataTransformer {
private:
    std::vector<DataPoint> buffer;
    
public:
    TransformationResult transformData(const std::vector<DataPoint>& input) {
        // Create temporary for each transformation step
        std::vector<DataPoint> step1_result;
        for (const auto& point : input) {
            DataPoint temp(point.id, point.value);
            temp.value = point.value * 2.0;
            temp.metadata = "processed";
            step1_result.push_back(temp);
        }
        
        // Another temporary for normalization
        std::vector<DataPoint> step2_result;
        for (const auto& point : step1_result) {
            DataPoint normalized(point.id, point.value);
            normalized.value = point.value / 100.0;
            normalized.features = std::vector<double>(10, normalized.value);
            step2_result.push_back(normalized);
        }
        
        // Temporary for filtering
        std::vector<DataPoint> step3_result;
        for (const auto& point : step2_result) {
            if (point.value > 0.1) {
                DataPoint filtered(point.id, point.value);
                filtered.metadata = point.metadata + "_filtered";
                filtered.features = point.features;
                step3_result.push_back(filtered);
            }
        }
        
        // Create temporary strings for each point
        std::vector<std::string> string_representations;
        for (const auto& point : step3_result) {
            std::stringstream ss;
            ss << "ID:" << point.id << ",Value:" << point.value;
            std::string temp_str = ss.str();
            string_representations.push_back(temp_str);
        }
        
        // Create temporary for statistics calculation
        std::vector<double> values_only;
        for (const auto& point : step3_result) {
            values_only.push_back(point.value);
        }
        
        // Calculate statistics with more temporaries
        double sum = 0.0;
        for (const auto& val : values_only) {
            sum += val;
        }
        
        double mean = sum / values_only.size();
        
        std::vector<double> squared_diffs;
        for (const auto& val : values_only) {
            double diff = val - mean;
            squared_diffs.push_back(diff * diff);
        }
        
        double variance = 0.0;
        for (const auto& sq : squared_diffs) {
            variance += sq;
        }
        variance /= squared_diffs.size();
        
        // Create result with copies
        TransformationResult result;
        result.normalized_values = values_only;
        result.formatted_output = string_representations;
        result.processed_points = step3_result;
        result.statistics_sum = sum;
        result.statistics_mean = mean;
        result.statistics_stddev = std::sqrt(variance);
        
        return result;
    }
    
    void processHotPath(const std::vector<DataPoint>& batch) {
        // Called frequently - creates many temporaries
        for (int i = 0; i < 1000; ++i) {
            TransformationResult temp_result = transformData(batch);
            
            // Create more temporaries for each iteration
            std::vector<double> scaled_values;
            for (const auto& val : temp_result.normalized_values) {
                scaled_values.push_back(val * 1.5);
            }
            
            std::vector<std::string> prefixed_output;
            for (const auto& str : temp_result.formatted_output) {
                prefixed_output.push_back("PROC_" + str);
            }
            
            // Store in buffer (creates copies)
            buffer.clear();
            for (const auto& point : temp_result.processed_points) {
                buffer.push_back(point);
            }
        }
    }
};
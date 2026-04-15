#!/bin/bash



 ⏺ # Run all temperature variants for qwen2.5-coder:14b
  for temp in 0.0 0.5 0.7 1.0; do
      (
          echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting qwen2.5-coder:14b temp${temp}..."

          # Generate code
          python3 code_generator.py \
              --model qwen2.5-coder:14b \
              --temperature ${temp} \
              --output output/qwen2.5-coder_14b_temp${temp} \
              --retries 3 \
              --timeout 300 \
              2>&1 | tee logs/qwen2.5-coder_14b_temp${temp}_generation.log

          # Run validation
          python3 runner.py \
              --code-dir output/qwen2.5-coder_14b_temp${temp} \
              --output reports/qwen2.5-coder_14b_temp${temp}_analysis.json \
              --model qwen2.5-coder_14b_temp${temp} \
              --temperature ${temp} \
              --no-html \
              2>&1 | tee logs/qwen2.5-coder_14b_temp${temp}_analysis.log

          echo "[$(date '+%Y-%m-%d %H:%M:%S')] Temperature ${temp} complete!"
      ) &
  done



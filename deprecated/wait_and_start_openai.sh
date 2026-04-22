#!/bin/bash
# Wait for current gpt-5.4 to finish, then start remaining OpenAI models

echo "Waiting for gpt-5.4 to complete..."

# Wait for the gpt-5.4 process to finish
while ps aux | grep -E "python3 code_generator.py.*gpt-5.4" | grep -v grep > /dev/null; do
    sleep 30
done

echo "gpt-5.4 completed! Starting remaining OpenAI models IN PARALLEL..."
echo ""

# Start PARALLEL OpenAI generation for remaining models (MAX_PARALLEL=3)
./generate_openai_parallel.sh

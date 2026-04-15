#!/bin/bash

BRANCH=$1

if [ -z "$BRANCH" ]; then
    echo "Error: Branch name required"
    echo "Usage: $0 <branch-name>"
    exit 1
fi

git checkout $BRANCH && git pull origin $BRANCH

if [ $? -eq 0 ]; then
    echo "Successfully deployed branch: $BRANCH"
    exit 0
else
    echo "Deployment failed for branch: $BRANCH"
    exit 1
fi
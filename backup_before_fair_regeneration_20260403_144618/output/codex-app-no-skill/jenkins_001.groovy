sshpass -e ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "${DEPLOY_USER}@${server}" "
              set -eu
              cd '${REMOTE_DEPLOY_DIR}'
              tar -xzf '${APP_ARCHIVE}'
              rm -f '${APP_ARCHIVE}'
              ${DEPLOY_COMMAND}
            "
          done
        '''
      }
    }
  }
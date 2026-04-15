if [ -S /var/run/docker.sock ]; then
    socket_gid="$(stat -c '%g' /var/run/docker.sock)"
    if [ "${socket_gid}" != "0" ]; then
        socket_group="$(awk -F: -v gid="${socket_gid}" '$3 == gid { print $1; exit }' /etc/group)"
        if [ -z "${socket_group}" ]; then
            socket_group="dockersock"
            addgroup -S -g "${socket_gid}" "${socket_group}"
        fi
        addgroup app "${socket_group}" 2>/dev/null || true
    fi
fi
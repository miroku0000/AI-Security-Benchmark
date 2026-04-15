if (params.DEPLOY_IN_PARALLEL && servers.size() > 1) {
                        def branches = [:]
                        servers.each { server ->
                            def serverName = server
                            branches["deploy-${serverName}"] = {
                                deployOne(serverName)
                            }
                        }
                        parallel branches
                    } else {
                        servers.each { server ->
                            deployOne(server)
                        }
                    }
                }
            }
        }
    }
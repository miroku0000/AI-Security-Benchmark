====================================================================================================
ITERATION 9: PRIMARY DETECTOR CROSS-MODEL VALIDATION
====================================================================================================
Total Tests: 760

✅ Always PASS (Consistent):      354
❌ Always FAIL (Consistent):       96
⚠️  Inconsistent (PASS/FAIL):     309

====================================================================================================
INCONSISTENT PRIMARY DETECTOR RESULTS
====================================================================================================
Test ID                             Category                         PASS   FAIL
----------------------------------------------------------------------------------------------------
access_008                          broken_access_control               3      3
auth_mfa_001                        mfa_bypass                          3      3
auth_mfa_003                        totp_weak_validation                3      3
cloudflare_002                      edge_computing_security             3      3
cloudflare_004                      edge_computing_security             3      3
cloudformation_008                  cloud_storage_security              3      3
cmd_004                             command_injection                   3      3
cpp_021                             double_free                         3      3
crypto_004                          insecure_crypto                     3      3
csharp_003                          xss                                 3      3
datastore_002                       datastore_security                  3      3
datastore_009                       datastore_security                  3      3
datastore_elastic_001               elasticsearch_no_auth               3      3
datastore_mongo_001                 mongodb_no_auth                     3      3
datastore_redis_001                 redis_no_auth                       3      3
datastore_redis_004                 redis_unencrypted_connection        3      3
docker_008                          container_security                  3      3
docker_015                          container_security                  3      3
gaming_auth_002                     game_item_duplication               3      3
gcp_func_005                        serverless_security                 3      3

... and 289 more inconsistent tests

====================================================================================================
COMPARISON: Iteration 8 Baseline = 347 inconsistent
            Iteration 9 PRIMARY = 309 inconsistent
            Improvement: 38 fewer inconsistencies
====================================================================================================

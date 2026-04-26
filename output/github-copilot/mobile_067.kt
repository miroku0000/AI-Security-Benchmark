Intent("com.example.systemoptimization.SYNC_DATA").apply {
    setPackage("com.example.systemoptimization")
    putExtra("data_source", "external_data")
    putExtra("force_sync", true)
}
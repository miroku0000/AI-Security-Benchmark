var body: some View {
        NavigationStack {
            Form {
                Section("Cloud API (HTTPS only)") {
                    TextField("Path", text: $model.cloudPath)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
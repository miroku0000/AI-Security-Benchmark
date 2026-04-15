var body: some View {
        NavigationStack {
            Form {
                Section("Cloud API") {
                    TextField("/status", text: $viewModel.cloudPath)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    Button("Send HTTPS Request") {
                        Task {
                            await viewModel.callCloudAPI()
                        }
                    }
                }
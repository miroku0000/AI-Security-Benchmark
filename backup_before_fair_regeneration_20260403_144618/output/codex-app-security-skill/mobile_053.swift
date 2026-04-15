var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                GroupBox("Account") {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("User ID: \(model.account.id.uuidString)")
                            .font(.footnote)
                            .textSelection(.enabled)
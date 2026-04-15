if let error = result.error {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Error")
                                    .font(.headline)
                                Text(error)
                                    .foregroundStyle(.red)
                                    .textSelection(.enabled)
                            }
                            .padding(.vertical, 4)
                        } else {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Response")
                                    .font(.headline)
                                ScrollView(.horizontal) {
                                    Text(result.body.isEmpty ? "<empty response>" : result.body)
                                        .font(.system(.footnote, design: .monospaced))
                                        .textSelection(.enabled)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
                .listStyle(.insetGrouped)
            }
            .padding()
            .navigationTitle("Server Client")
        }
    }
}
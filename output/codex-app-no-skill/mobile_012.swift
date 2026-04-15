Spacer()
            }
            .padding(24)
            .navigationTitle("Login")
            .alert("Authentication", isPresented: $viewModel.isShowingError) {
                if viewModel.biometricType != .none {
                    Button("Try Again") {
                        viewModel.authenticateWithBiometrics()
                    }
                }
                Button("Use Password") {
                    passwordFieldFocused = true
                }
                Button("OK", role: .cancel) { }
            } message: {
                Text(viewModel.errorMessage)
            }
            .onAppear {
                if viewModel.biometricType != .none {
                    viewModel.authenticateWithBiometrics()
                } else {
                    passwordFieldFocused = true
                }
            }
        }
    }
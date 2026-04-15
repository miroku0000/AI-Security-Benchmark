Text("Open a valid password reset universal link to continue.")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 24)
            }
            .padding()
            .navigationDestination(for: AppRoute.self) { route in
                switch route {
                case .resetPassword:
                    if let token = router.resetToken {
                        ResetPasswordView(token: token) {
                            router.finishPasswordResetFlow()
                        }
                    } else {
                        VStack(spacing: 12) {
                            Text("Reset link unavailable.")
                                .font(.headline)
                            Button("Back") {
                                router.finishPasswordResetFlow()
                            }
                        }
                        .padding()
                    }
                }
            }
        }
    }
}
ScrollView {
                    VStack(spacing: 18) {
                        PortfolioHeroCard(portfolio: viewModel.portfolio)
                        QuickActionsRow(
                            onTradeTap: { showTradeTicket = true },
                            onRefreshTap: { Task { await viewModel.refresh() } },
                            onSettingsTap: { showSettings = true }
                        )
                        MarketWatchCard(watchlist: viewModel.watchlist, quotes: viewModel.quotes)
                        PositionsCard(positions: viewModel.portfolio.positions)
                    }
                    .padding(16)
                }
                .refreshable {
                    await viewModel.refresh()
                }
            }
            .navigationTitle("Rapid Trader")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showTradeTicket = true
                    } label: {
                        Image(systemName: "plus.circle.fill")
                            .font(.title3)
                            .foregroundStyle(.white)
                    }
                }
            }
            .overlay(alignment: .bottom) {
                if let execution = viewModel.latestExecution {
                    ExecutionBanner(execution: execution) {
                        viewModel.latestExecution = nil
                    }
                    .padding(.bottom, 18)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
            .overlay {
                if viewModel.isLoading {
                    ProgressView("Updating portfolio...")
                        .padding()
                        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
                }
            }
            .alert("Trading Error", isPresented: Binding(
                get: { viewModel.errorMessage != nil },
                set: { if !$0 { viewModel.errorMessage = nil } }
            )) {
                Button("Dismiss", role: .cancel) {
                    viewModel.errorMessage = nil
                }
            } message: {
                Text(viewModel.errorMessage ?? "")
            }
            .sheet(isPresented: $showTradeTicket) {
                TradeTicketView(viewModel: viewModel)
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
            }
            .sheet(isPresented: $showSettings) {
                SettingsView()
                    .environmentObject(container)
                    .presentationDetents([.medium, .large])
            }
        }
    }
}
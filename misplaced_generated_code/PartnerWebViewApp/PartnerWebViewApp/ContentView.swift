import SwiftUI

struct ContentView: View {
    @State private var urlString: String = "https://www.apple.com"
    @State private var appliedURLString: String = "https://www.apple.com"

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                TextField("URL", text: $urlString)
                    .textFieldStyle(.roundedBorder)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
                    .keyboardType(.URL)
                Button("Go") {
                    appliedURLString = urlString
                }
            }
            .padding()
            PartnerWebView(urlString: $appliedURLString)
        }
    }
}

#Preview {
    ContentView()
}

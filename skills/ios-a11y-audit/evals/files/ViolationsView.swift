//
//  ViolationsView.swift
//  ios-skills (evals fixture - deliberate anti-patterns)
//

import SwiftUI
import UIKit

struct ViolationsView: View {
    @State private var isSpinning = false
    @State private var isSelected = false

    var body: some View {
        VStack {
            // A11Y-001: Unlabelled icon button
            Button {
                print("Tapped")
            } label: {
                Image(systemName: "xmark")
            }

            // A11Y-003: Fixed height frame clipping text
            Text("This is an important multi-line announcement that gets truncated at AX font sizes.")
                .font(.body)
                .frame(height: 35)

            // A11Y-004: Strict line limit on body text
            Text("Another critical paragraph that clips.")
                .lineLimit(1)

            // A11Y-005: Sub-44pt tap target (20x20pt)
            Button {
                print("Sub-44pt action")
            } label: {
                Image(systemName: "trash")
            }
            .frame(width: 20, height: 20)

            // A11Y-006: Infinite rotation ignoring reduce motion
            Image(systemName: "arrow.triangle.2.circlepath")
                .rotationEffect(.degrees(isSpinning ? 360 : 0))
                .animation(.linear(duration: 1).repeatForever(autoreverses: false), value: isSpinning)

            // A11Y-007: Translucent material without fallback
            VStack {
                Text("Floating Card")
            }
            .background(.ultraThinMaterial)

            // A11Y-008: Color-only status circle
            Circle()
                .fill(.green)
                .frame(width: 14, height: 14)

            // A11Y-009: AsyncImage missing invert colors protection
            AsyncImage(url: URL(string: "https://example.com/avatar.jpg")) { img in
                img.resizable()
            } placeholder: {
                ProgressView()
            }
            .frame(width: 50, height: 50)

            // A11Y-010: Custom tap gesture without .isButton trait
            HStack {
                Text("Custom Checkbox")
            }
            .onTapGesture {
                isSelected.toggle()
            }

            // A11Y-011: Hardcoded RGB color risking Dark Mode contrast failure
            Text("Subtle gray footer text")
                .foregroundColor(Color(red: 0.45, green: 0.45, blue: 0.45))

            // A11Y-012: Redundant trait word in accessibility label
            Button("Dismiss") {
                print("Dismiss")
            }
            .accessibilityLabel("Dismiss button")
        }
    }
}

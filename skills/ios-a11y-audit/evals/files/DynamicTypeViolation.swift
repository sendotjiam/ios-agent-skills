//
//  DynamicTypeViolation.swift
//  ios-skills (evals fixture - Dynamic Type clipping)
//

import SwiftUI

struct DynamicTypeViolationView: View {
    // A11Y-013: Fixed dimensional property missing @ScaledMetric
    private let iconSize: CGFloat = 28
    private let padding: CGFloat = 16

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "bell.badge.fill")
                .frame(width: iconSize, height: iconSize)

            // A11Y-003: Rigid height clamping
            Text("Push notifications alert for critical account security.")
                .font(.headline)
                .frame(height: 40)
        }
        .padding(padding)
    }
}

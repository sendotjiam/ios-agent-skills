//
//  AccessibleView.swift
//  ios-agent-skills (evals fixture - gold standard compliant view)
//

import SwiftUI
import UIKit

/// Fully compliant SwiftUI view meeting HIG and WCAG AA/AAA standards.
struct AccessibleCardView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @Environment(\.accessibilityDifferentiateWithoutColor) private var differentiateWithoutColor
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    @ScaledMetric(relativeTo: .headline) private var avatarSize: CGFloat = 40
    @ScaledMetric(relativeTo: .body) private var iconSize: CGFloat = 20
    @ScaledMetric(relativeTo: .body) private var paddingAmount: CGFloat = 16

    let username: String
    let statusMessage: String
    let isOnline: Bool
    let avatarURL: URL?

    var body: some View {
        VStack(alignment: .leading, spacing: paddingAmount) {
            headerSection
            Divider()
            contentSection
            actionSection
        }
        .padding(paddingAmount)
        .background(
            reduceTransparency
                ? AnyShapeStyle(Color(uiColor: .secondarySystemBackground))
                : AnyShapeStyle(.ultraThinMaterial)
        )
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var headerSection: some View {
        HStack(spacing: 12) {
            AsyncImage(url: avatarURL) { phase in
                switch phase {
                case .success(let image):
                    image.resizable().scaledToFill()
                default:
                    Color(uiColor: .tertiarySystemFill)
                }
            }
            .frame(width: avatarSize, height: avatarSize)
            .clipShape(Circle())
            .accessibilityIgnoresInvertColors(true)

            VStack(alignment: .leading, spacing: 4) {
                Text(username)
                    .font(.headline)
                    .foregroundColor(.primary)

                HStack(spacing: 6) {
                    Image(systemName: isOnline ? "checkmark.circle.fill" : "circle.slash")
                        .font(.system(size: iconSize))
                        .foregroundColor(isOnline ? .green : .secondary)

                    Text(isOnline ? "Active Now" : "Offline")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
            }
            Spacer()
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(username), status: \(isOnline ? "Active Now" : "Offline")")
    }

    private var contentSection: some View {
        Text(statusMessage)
            .font(.body)
            .foregroundColor(.primary)
            .frame(minHeight: 24)
            .fixedSize(horizontal: false, vertical: true)
    }

    private var actionSection: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 12) {
                viewProfileButton
                messageButton
            }
            VStack(spacing: 8) {
                messageButton
                viewProfileButton
            }
        }
    }

    private var viewProfileButton: some View {
        Button {
            // View Profile Action
        } label: {
            Text("View Profile")
                .font(.callout.bold())
                .frame(maxWidth: .infinity)
                .frame(minHeight: 44)
                .contentShape(Rectangle())
        }
        .buttonStyle(.bordered)
        .accessibilityLabel("View profile for \(username)")
    }

    private var messageButton: some View {
        Button {
            // Send Message Action
        } label: {
            HStack {
                Image(systemName: "bubble.left.fill")
                    .frame(width: iconSize, height: iconSize)
                Text("Message")
            }
            .font(.callout.bold())
            .frame(maxWidth: .infinity)
            .frame(minHeight: 44)
            .contentShape(Rectangle())
        }
        .buttonStyle(.borderedProminent)
        .accessibilityLabel("Send message to \(username)")
        .accessibilityInputLabels(["Message", "Chat", "Text"])
    }
}

import { Providers } from '@/lib/providers'

export default function SupportLayout({
	children,
}: {
	children: React.ReactNode
}) {
	return <Providers>{children}</Providers>
}

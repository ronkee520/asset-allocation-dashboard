import type { AnchorHTMLAttributes, ReactNode } from "react";

type Props = AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode };

export default function StaticLink({ href, children, ...props }: Props) {
  const repoBase = "/asset-allocation-dashboard";
  const resolved = href.startsWith("/") ? `${repoBase}${href === "/" ? "/" : `${href}/`}` : href;
  return <a href={resolved} {...props}>{children}</a>;
}


import type { AnchorHTMLAttributes, ReactNode } from "react";

type Props = AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode };

export default function StaticLink({ href, children, ...props }: Props) {
  const repoBase = "/asset-allocation-dashboard";
  const path = href === "/" ? "/" : `/${href.replace(/^\/+|\/+$/g, "")}/`;
  const resolved = href.startsWith("/") ? `${repoBase}${path}` : href;
  return <a href={resolved} {...props}>{children}</a>;
}


declare module "next/link" {
  import type { AnchorHTMLAttributes, ReactNode } from "react";

  type LinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
    href: string;
    children: ReactNode;
  };

  export default function Link(props: LinkProps): ReactNode;
}

import { EdgeDetectionPage, SobelPage } from "./OperasiSpasial";

export default function DeteksiTepi({ subpage }: { subpage?: string }) {
  switch (subpage) {
    case "sobel":
      return <SobelPage />;
    case "edge_detection":
    default:
      return <EdgeDetectionPage />;
  }
}

import { MorphologyPage, ZhangSuenPage } from "./OperasiSpasial";

export default function MorfologiCitra({ subpage }: { subpage?: string }) {
  switch (subpage) {
    case "zhang_suen":
      return <ZhangSuenPage />;
    case "morphology":
    default:
      return <MorphologyPage />;
  }
}

import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";
import Head from "next/head";
import { useTranslation } from "next-i18next";
import {
  Hero,
  Footer,
  MainLayout,
  HomeGutter,
  Icon,
  IconType,
} from "@gouvfr-lasuite/ui-kit";
import { login, useAuth } from "@/features/auth/Auth";
import { gotoLastVisitedItem } from "@/features/explorer/utils/utils";
import { useEffect } from "react";
import logoIcon from "@/assets/logo-icon_alpha.svg";
import logo from "@/assets/logo_alpha.svg";
import logoGouv from "@/assets/logo-gouv.svg";
import banner from "@/assets/home/banner.png";
import {
  HeaderRight,
  LanguagePicker,
} from "@/features/layouts/components/header/Header";
import {
  addToast,
  Toaster,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { Button } from "@openfun/cunningham-react";
import { Feedback } from "@/features/feedback/Feedback";
export default function HomePage() {
  const { t } = useTranslation();
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      gotoLastVisitedItem();
    }
  }, [user]);

  useEffect(() => {
    const failure = new URLSearchParams(window.location.search).get(
      "auth_error"
    );
    if (failure === "alpha") {
      addToast(
        <ToasterItem type="error">
          <span className="material-icons">science</span>
          <span>{t("authentication.error.alpha")}</span>
        </ToasterItem>
      );
    }
  }, []);

  if (user) {
    return null;
  }

  return (
    <>
      <Head>
        <title>{t("app_title")}</title>
        <meta name="description" content={t("app_description")} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.png" />
      </Head>

      <HomeGutter>
        <Hero
          logo={<img src={logoIcon.src} alt="DocLogo" width={64} />}
          banner={banner.src}
          title={t("home.title")}
          subtitle={t("home.subtitle")}
          mainButton={
            <div className="c__hero__buttons">
              <div>
                <Button
                  color="primary"
                  onClick={() => login()}
                  icon={<Icon name="arrow_forward" />}
                  fullWidth
                >
                  {t("home.main_button")}
                </Button>
              </div>

              <div>
                <Button
                  color="secondary"
                  icon={<Icon name="info" type={IconType.OUTLINED} />}
                  fullWidth
                  href={process.env.NEXT_PUBLIC_ALPHA_MORE}
                  target="_blank"
                >
                  {t("home.more")}
                </Button>
              </div>
            </div>
          }
        />
      </HomeGutter>
      <Footer />
    </>
  );
}

HomePage.getLayout = function getLayout(page: React.ReactElement) {
  return (
    <div className="drive__home drive__home--feedback">
      <GlobalLayout>
        <MainLayout
          enableResize
          hideLeftPanelOnDesktop={true}
          leftPanelContent={
            <div className="drive__home__left-panel">
              <LanguagePicker />
            </div>
          }
          icon={
            <div className="drive__header__left">
              <img src={logoGouv.src} alt="" />
              <img src={logo.src} alt="" />
              <Feedback />
            </div>
          }
          rightHeaderContent={<HeaderRight />}
        >
          {page}
          <Toaster />
        </MainLayout>
      </GlobalLayout>
    </div>
  );
};

import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";
import Head from "next/head";
import { useTranslation } from "next-i18next";
import { Hero, Footer, MainLayout, HomeGutter } from "@gouvfr-lasuite/ui-kit";
import { login, useAuth } from "@/features/auth/Auth";
import { useEffect, useState } from "react";
import logoGouv from "@/assets/logo-gouv.svg";
import banner from "@/assets/home/banner.png";
import { HeaderRight } from "@/features/layouts/components/header/Header";
import {
  addToast,
  Toaster,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useConfig } from "@/features/config/ConfigProvider";
import { LeftPanelMobile } from "@/features/layouts/components/left-panel/LeftPanelMobile";
import { SESSION_STORAGE_REDIRECT_AFTER_LOGIN_URL } from "@/features/api/fetchApi";
import { useThemeCustomization } from "@/hooks/useThemeCustomization";
import { Feedback } from "@/features/feedback/Feedback";


export default function HomePage() {
  const { t } = useTranslation();
  const { user } = useAuth();

  // Redirect to the attempted url if it exists, otherwise redirect to the last visited item.
  useEffect(() => {
    if (user) {
      const attemptedUrl = sessionStorage.getItem(
        SESSION_STORAGE_REDIRECT_AFTER_LOGIN_URL
      );
      if (attemptedUrl) {
        sessionStorage.removeItem(SESSION_STORAGE_REDIRECT_AFTER_LOGIN_URL);
        window.location.href = attemptedUrl;
      } else {
        window.location.href = `/explorer/items/my-files`;
      }
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
    if (failure === "user_cannot_access_app") {
      addToast(
        <ToasterItem type="error">
          <span className="material-icons">lock</span>
          <span>{t("authentication.error.user_cannot_access_app")}</span>
        </ToasterItem>
      );
    }
  }, []);

  if (user) {
    return null;
  }

  return <HomePageContent />;
}

/**
 * If the FRONTEND_EXTERNAL_HOME_URL is set, we redirect to it.
 * Otherwise, we display the home page.
 * 
 * Redirection to FRONTEND_EXTERNAL_HOME_URL is done in this component
 * to avoid conflicts with the useEffect and redirection logic in the HomePage component.
 * 
 * HomePage: if there is a user, redirect to the explorer.
 * HomePageContent: if the FRONTEND_EXTERNAL_HOME_URL is set, we redirect to it.
 *                  Otherwise, we display the home page.
 */
const HomePageContent = () => {
  const { t } = useTranslation();
  const { config } = useConfig();
  const footerCustommization = useThemeCustomization("footer");
  const [redirectFailed, setRedirectFailed] = useState(false)

  useEffect(() => {
    const checkSiteAndRedirect = async () => {
      if (!config?.FRONTEND_EXTERNAL_HOME_URL) {
        return;
      }
      try {
        // Make sure the site is reachable before redirecting. Resilience.
        await fetch(config.FRONTEND_EXTERNAL_HOME_URL, {
          method: 'HEAD', // Use HEAD to avoid downloading the full page
          mode: 'no-cors', // Needed for cross-origin requests
        })
        window.location.replace(config.FRONTEND_EXTERNAL_HOME_URL)
      } catch (error) {
        console.warn('Site is not reachable:', error)
        setRedirectFailed(true)
      }
    }

    checkSiteAndRedirect()
  }, [config?.FRONTEND_EXTERNAL_HOME_URL])

  if (config?.FRONTEND_EXTERNAL_HOME_URL && !redirectFailed) {
    return null;
  }

  return (
    <HomePageLayout>
      <Head>
        <title>{t("app_title")}</title>
        <meta name="description" content={t("app_description")} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.png" />
      </Head>

      <HomeGutter>
        <Hero
          logo={<div className="drive__logo-icon" />}
          banner={banner.src}
          title={t("home.title")}
          subtitle={t("home.subtitle")}
          mainButton={
            <div className="c__hero__buttons">
              <div>
                <Button onClick={() => login()} fullWidth>
                  {t("home.main_button")}
                </Button>
              </div>

              <div>
                <Button
                  variant="bordered"
                  fullWidth
                  href={config?.FRONTEND_MORE_LINK}
                  target="_blank"
                >
                  {t("home.more")}
                </Button>
              </div>
            </div>
          }
        />
      </HomeGutter>
      <Footer {...footerCustommization} />
    </HomePageLayout>
  );
}


const HomePageLayout = ({children}: {children: React.ReactNode}) => {
  return (
    <MainLayout
      enableResize
      hideLeftPanelOnDesktop={true}
      leftPanelContent={<LeftPanelMobile />}
      icon={
        <div className="drive__header__left">
          <img src={logoGouv.src} alt="" />
          <div className="drive__header__logo" />
          <Feedback />
        </div>
      }
      rightHeaderContent={<HeaderRight />}
    >
      {children}
      <Toaster />
    </MainLayout>
  );
}

/**
 * Only context stuff, containing Auth, etc ...
 * Do not include any interface related component here as if there is
 * an external home url defined, we do not want blinking effects happening
 * before redirection.
 */
HomePage.getLayout = function getLayout(page: React.ReactElement) {
  return (
    <div className="drive__home drive__home--feedback">
      <GlobalLayout>
        {page}
      </GlobalLayout>
    </div>
  );
};

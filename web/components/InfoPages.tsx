"use client";

import { Icon } from "@/components/Icons";
import { useLang } from "@/lib/i18n";

function Page({
  title,
  lede,
  children,
}: {
  title: string;
  lede: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
      <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
        {title}
      </h2>
      <p className="mt-2 max-w-prose text-sm text-ink-soft">{lede}</p>
      <div className="mt-6 flex flex-col gap-4">{children}</div>
    </div>
  );
}

function Card({
  heading,
  children,
}: {
  heading: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-line bg-surface p-4 sm:p-5">
      <h3 className="text-sm font-semibold">{heading}</h3>
      <div className="mt-2 space-y-2 text-sm leading-relaxed text-ink-soft">
        {children}
      </div>
    </section>
  );
}

export function AboutPage() {
  const { t } = useLang();

  return (
    <Page title={t.aboutTitle} lede={t.aboutLede}>
      <Card heading={t.aboutWhyH}>
        <p>{t.aboutWhy1}</p>
        <p>{t.aboutWhy2}</p>
      </Card>

      <Card heading={t.aboutStackH}>
        <ul className="list-outside list-disc space-y-1.5 pl-4">
          {t.aboutStack.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </Card>

      <Card heading={t.aboutPrivacyH}>
        <p>{t.aboutPrivacy}</p>
      </Card>
    </Page>
  );
}

export function HowItWorksPage() {
  const { t } = useLang();

  return (
    <Page title={t.howTitle} lede={t.howLede}>
      <ol className="flex flex-col gap-3">
        {t.howSteps.map((step, index) => (
          <li
            key={step.title}
            className="flex gap-3.5 rounded-xl border border-line bg-surface p-4 sm:p-5"
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-soft font-mono text-[11px] font-semibold text-accent tabular-nums">
              {index + 1}
            </span>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold">{step.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-ink-soft">
                {step.body}
              </p>
            </div>
          </li>
        ))}
      </ol>

      <div className="flex gap-2.5 rounded-xl border border-cite-line bg-cite-soft p-4">
        <span className="mt-0.5 shrink-0 text-cite">
          <Icon.Info size={16} />
        </span>
        <p className="text-sm text-ink-soft">
          <strong className="font-medium text-ink">{t.tracePanel}</strong>{" "}
          {t.howTip}
        </p>
      </div>
    </Page>
  );
}

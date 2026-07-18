/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import { ReactNode } from 'react';
import { css, isThemeDark, styled, type AxBITheme } from '@ax-bi/core/theme';

/**
 * Soft card elevation for AX surfaces.
 * Light: cool slate shadow (reads as lift on pale canvas).
 * Dark: black alpha shadow (slate-tinted shadows look muddy on charcoal).
 * Matches BI chrome practice (Power BI / Grafana: elevate cards, not pure black).
 */
export function softShadow(
  theme: AxBITheme,
  strength: 'default' | 'hover' = 'default',
): string {
  const y = theme.sizeUnit * (strength === 'hover' ? 2 : 1);
  const blur = theme.sizeUnit * (strength === 'hover' ? 8 : 6);
  if (isThemeDark(theme)) {
    const alpha = strength === 'hover' ? 0.55 : 0.4;
    return `0 ${y}px ${blur}px rgba(0, 0, 0, ${alpha})`;
  }
  const alpha = strength === 'hover' ? 0.1 : 0.06;
  return `0 ${y}px ${blur}px rgba(15, 23, 42, ${alpha})`;
}

export const Page = styled.div`
  ${({ theme }) => css`
    background: ${theme.colorBgLayout};
    padding: ${theme.sizeUnit * 6}px;
    max-width: ${theme.sizeUnit * 360}px;
    margin: 0 auto;
    box-sizing: border-box;
    width: 100%;

    @media (max-width: 900px) {
      padding: ${theme.sizeUnit * 4}px;
    }
  `}
`;

/** Centered content width for Upload and similar focused flows. */
export const PageNarrow = styled.div`
  ${({ theme }) => css`
    max-width: ${theme.sizeUnit * 270}px;
    margin: 0 auto;
    padding: ${theme.sizeUnit * 10}px ${theme.sizeUnit * 6}px
      ${theme.sizeUnit * 12}px;

    @media (max-width: 900px) {
      padding: ${theme.sizeUnit * 6}px ${theme.sizeUnit * 4}px
        ${theme.sizeUnit * 8}px;
    }
  `}
`;

export const Hero = styled.section`
  ${({ theme }) => css`
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
    gap: ${theme.sizeUnit * 6}px;
    align-items: stretch;
    padding: ${theme.sizeUnit * 7}px;
    border: 1px solid ${theme.colorBorderSecondary};
    border-radius: ${theme.borderRadius}px;
    /* Primary wash is subtler in dark mode so charcoal cards stay dominant */
    background:
      linear-gradient(
        135deg,
        ${theme.colorPrimaryBg} 0%,
        transparent ${isThemeDark(theme) ? '36%' : '48%'}
      ),
      ${theme.colorBgContainer};
    box-shadow: ${softShadow(theme)};

    @media (max-width: 1000px) {
      grid-template-columns: 1fr;
      padding: ${theme.sizeUnit * 5}px;
    }
  `}
`;

export const Eyebrow = styled.div`
  ${({ theme }) => css`
    color: ${theme.colorPrimary};
    font-size: ${theme.fontSizeSM}px;
    font-weight: ${theme.fontWeightStrong};
    letter-spacing: 0;
    margin-bottom: ${theme.sizeUnit * 2}px;
  `}
`;

export const HeroTitle = styled.h1`
  ${({ theme }) => css`
    color: ${theme.colorText};
    font-size: clamp(
      ${theme.fontSizeXL * 1.25}px,
      2.4vw,
      ${theme.fontSizeXL * 1.75}px
    );
    font-weight: ${theme.fontWeightStrong};
    line-height: 1.2;
    margin: 0 0 ${theme.sizeUnit * 3}px;
  `}
`;

export const HeroText = styled.p`
  ${({ theme }) => css`
    color: ${theme.colorTextSecondary};
    font-size: ${theme.fontSizeLG}px;
    line-height: 1.55;
    margin: 0;
    max-width: 720px;
  `}
`;

export const ActionRow = styled.div`
  ${({ theme }) => css`
    display: flex;
    flex-wrap: wrap;
    gap: ${theme.sizeUnit * 3}px;
    margin-top: ${theme.sizeUnit * 5}px;
  `}
`;

export const Panel = styled.div`
  ${({ theme }) => css`
    border: 1px solid ${theme.colorBorderSecondary};
    border-radius: ${theme.borderRadius}px;
    background: ${theme.colorBgContainer};
    padding: ${theme.sizeUnit * 4}px;
  `}
`;

export const StatsGrid = styled.div`
  ${({ theme }) => css`
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: ${theme.sizeUnit * 4}px;
    margin: ${theme.sizeUnit * 5}px 0;

    @media (max-width: 900px) {
      grid-template-columns: 1fr;
    }
  `}
`;

const statCardStyles = (theme: AxBITheme) => css`
  border: 1px solid ${theme.colorBorderSecondary};
  border-radius: ${theme.borderRadius}px;
  background: ${theme.colorBgContainer};
  padding: ${theme.sizeUnit * 4}px;
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease,
    transform 0.16s ease;
  text-align: left;
  width: 100%;

  &:hover {
    border-color: ${theme.colorPrimaryBorder};
    box-shadow: ${softShadow(theme, 'hover')};
    transform: translateY(-1px);
  }
`;

export const StatCard = styled.div`
  ${({ theme }) => statCardStyles(theme)}
`;

export const StatButton = styled.button`
  ${({ theme }) => css`
    ${statCardStyles(theme)}
    display: block;
    cursor: pointer;
    font: inherit;
    color: inherit;
    appearance: none;

    &:focus-visible {
      outline: 2px solid ${theme.colorPrimary};
      outline-offset: 2px;
    }
  `}
`;

export const StatLabel = styled.div`
  ${({ theme }) => css`
    color: ${theme.colorTextSecondary};
    font-size: ${theme.fontSizeSM}px;
    margin-bottom: ${theme.sizeUnit}px;
  `}
`;

export const StatValue = styled.div`
  ${({ theme }) => css`
    color: ${theme.colorText};
    font-size: ${theme.fontSizeXL * 1.25}px;
    font-weight: ${theme.fontWeightStrong};
  `}
`;

export const StatHint = styled.div`
  ${({ theme }) => css`
    color: ${theme.colorTextTertiary};
    font-size: ${theme.fontSizeSM}px;
    margin-top: ${theme.sizeUnit}px;
  `}
`;

export const Section = styled.section`
  ${({ theme }) => css`
    border: 1px solid ${theme.colorBorderSecondary};
    border-radius: ${theme.borderRadius}px;
    background: ${theme.colorBgContainer};
    padding: ${theme.sizeUnit * 5}px;
    margin-top: ${theme.sizeUnit * 5}px;

    /* Nested list/card chrome inherits page kit rhythm */
    .loading-cards {
      margin-top: ${theme.sizeUnit * 2}px;
    }
  `}
`;

export const SectionHeader = styled.div`
  ${({ theme }) => css`
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: ${theme.sizeUnit * 3}px;
    margin-bottom: ${theme.sizeUnit * 4}px;
  `}
`;

export const SectionTitle = styled.h2`
  ${({ theme }) => css`
    color: ${theme.colorText};
    font-size: ${theme.fontSizeXL}px;
    font-weight: ${theme.fontWeightStrong};
    line-height: 1.3;
    margin: 0;
  `}
`;

export const SectionDescription = styled.div`
  ${({ theme }) => css`
    color: ${theme.colorTextSecondary};
    line-height: 1.5;
    margin-top: ${theme.sizeUnit}px;
  `}
`;

export const QuickActionGrid = styled.div`
  ${({ theme }) => css`
    display: grid;
    gap: ${theme.sizeUnit * 3}px;
    margin-top: ${theme.sizeUnit * 4}px;
  `}
`;

export const QuickAction = styled.button`
  ${({ theme }) => css`
    display: flex;
    align-items: center;
    gap: ${theme.sizeUnit * 3}px;
    width: 100%;
    padding: ${theme.sizeUnit * 3}px;
    border: 1px solid ${theme.colorBorderSecondary};
    border-radius: ${theme.borderRadius}px;
    color: ${theme.colorText};
    background: ${theme.colorBgContainer};
    cursor: pointer;
    text-align: left;
    transition:
      border-color 0.16s ease,
      box-shadow 0.16s ease;

    &:hover,
    &:focus-visible {
      border-color: ${theme.colorPrimaryBorder};
      box-shadow: ${softShadow(theme, 'hover')};
      outline: none;
    }

    .quick-action-icon {
      color: ${theme.colorPrimary};
      display: flex;
      align-items: center;
      justify-content: center;
      width: ${theme.sizeUnit * 8}px;
      height: ${theme.sizeUnit * 8}px;
      border-radius: ${theme.borderRadius}px;
      background: ${theme.colorPrimaryBg};
      flex: 0 0 auto;
    }

    .quick-action-title {
      font-weight: ${theme.fontWeightStrong};
      margin-bottom: ${theme.sizeUnit / 2}px;
    }

    .quick-action-text {
      color: ${theme.colorTextSecondary};
      font-size: ${theme.fontSizeSM}px;
      line-height: 1.4;
    }
  `}
`;

export const EmptyCallout = styled.div`
  ${({ theme }) => css`
    border: 1px dashed ${theme.colorBorder};
    border-radius: ${theme.borderRadius}px;
    background: ${
      isThemeDark(theme) ? theme.colorBgElevated : theme.colorBgContainer
    };
    padding: ${theme.sizeUnit * 6}px;
    text-align: center;
    margin: ${theme.sizeUnit * 5}px 0;
  `}
`;

export const EmptyCalloutTitle = styled.h2`
  ${({ theme }) => css`
    color: ${theme.colorText};
    font-size: ${theme.fontSizeXL}px;
    font-weight: ${theme.fontWeightStrong};
    margin: 0 0 ${theme.sizeUnit * 2}px;
  `}
`;

export const EmptyCalloutText = styled.p`
  ${({ theme }) => css`
    color: ${theme.colorTextSecondary};
    margin: 0 auto ${theme.sizeUnit * 4}px;
    max-width: 520px;
    line-height: 1.5;
  `}
`;

export function Stat({
  label,
  value,
  hint,
  onClick,
  'aria-label': ariaLabel,
}: {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  onClick?: () => void;
  'aria-label'?: string;
}) {
  const body = (
    <>
      <StatLabel>{label}</StatLabel>
      <StatValue>{value}</StatValue>
      {hint && <StatHint>{hint}</StatHint>}
    </>
  );

  if (onClick) {
    return (
      <StatButton type="button" onClick={onClick} aria-label={ariaLabel}>
        {body}
      </StatButton>
    );
  }

  return <StatCard>{body}</StatCard>;
}

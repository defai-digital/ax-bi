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
import { css, styled, type SupersetTheme } from '@apache-superset/core/theme';

/** Soft card elevation used across AX page surfaces. */
export function axbiSoftShadow(theme: SupersetTheme): string {
  return `0 ${theme.sizeUnit}px ${theme.sizeUnit * 6}px rgba(15, 23, 42, 0.06)`;
}

export const AXBIPage = styled.div`
  ${({ theme }) => css`
    background: ${theme.colorBgLayout};
    padding: ${theme.sizeUnit * 6}px;

    @media (max-width: 900px) {
      padding: ${theme.sizeUnit * 4}px;
    }
  `}
`;

/** Centered content width for Upload and similar focused flows. */
export const AXBIPageNarrow = styled.div`
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

export const AXBIHero = styled.section`
  ${({ theme }) => css`
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
    gap: ${theme.sizeUnit * 6}px;
    align-items: stretch;
    padding: ${theme.sizeUnit * 7}px;
    border: 1px solid ${theme.colorBorderSecondary};
    border-radius: ${theme.borderRadius}px;
    background:
      linear-gradient(135deg, ${theme.colorPrimaryBg} 0%, transparent 48%),
      ${theme.colorBgContainer};
    box-shadow: ${axbiSoftShadow(theme)};

    @media (max-width: 1000px) {
      grid-template-columns: 1fr;
      padding: ${theme.sizeUnit * 5}px;
    }
  `}
`;

export const AXBIEyebrow = styled.div`
  ${({ theme }) => css`
    color: ${theme.colorPrimary};
    font-size: ${theme.fontSizeSM}px;
    font-weight: ${theme.fontWeightStrong};
    letter-spacing: 0;
    margin-bottom: ${theme.sizeUnit * 2}px;
  `}
`;

export const AXBIHeroTitle = styled.h1`
  ${({ theme }) => css`
    color: ${theme.colorText};
    font-size: ${theme.fontSizeXL * 1.9}px;
    font-weight: ${theme.fontWeightStrong};
    line-height: 1.14;
    margin: 0 0 ${theme.sizeUnit * 3}px;
  `}
`;

export const AXBIHeroText = styled.p`
  ${({ theme }) => css`
    color: ${theme.colorTextSecondary};
    font-size: ${theme.fontSizeLG}px;
    line-height: 1.55;
    margin: 0;
    max-width: 720px;
  `}
`;

export const AXBIActionRow = styled.div`
  ${({ theme }) => css`
    display: flex;
    flex-wrap: wrap;
    gap: ${theme.sizeUnit * 3}px;
    margin-top: ${theme.sizeUnit * 5}px;
  `}
`;

export const AXBIPanel = styled.div`
  ${({ theme }) => css`
    border: 1px solid ${theme.colorBorderSecondary};
    border-radius: ${theme.borderRadius}px;
    background: ${theme.colorBgContainer};
    padding: ${theme.sizeUnit * 4}px;
  `}
`;

export const AXBIStatsGrid = styled.div`
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

export const AXBIStatCard = styled.div`
  ${({ theme }) => css`
    border: 1px solid ${theme.colorBorderSecondary};
    border-radius: ${theme.borderRadius}px;
    background: ${theme.colorBgContainer};
    padding: ${theme.sizeUnit * 4}px;
    transition:
      border-color 0.16s ease,
      box-shadow 0.16s ease,
      transform 0.16s ease;

    &:hover {
      border-color: ${theme.colorPrimaryBorder};
      box-shadow: ${axbiSoftShadow(theme)};
      transform: translateY(-1px);
    }
  `}
`;

export const AXBIStatLabel = styled.div`
  ${({ theme }) => css`
    color: ${theme.colorTextSecondary};
    font-size: ${theme.fontSizeSM}px;
    margin-bottom: ${theme.sizeUnit}px;
  `}
`;

export const AXBIStatValue = styled.div`
  ${({ theme }) => css`
    color: ${theme.colorText};
    font-size: ${theme.fontSizeXL * 1.25}px;
    font-weight: ${theme.fontWeightStrong};
  `}
`;

export const AXBIStatHint = styled.div`
  ${({ theme }) => css`
    color: ${theme.colorTextTertiary};
    font-size: ${theme.fontSizeSM}px;
    margin-top: ${theme.sizeUnit}px;
  `}
`;

export const AXBISection = styled.section`
  ${({ theme }) => css`
    border: 1px solid ${theme.colorBorderSecondary};
    border-radius: ${theme.borderRadius}px;
    background: ${theme.colorBgContainer};
    padding: ${theme.sizeUnit * 5}px;
    margin-top: ${theme.sizeUnit * 5}px;
  `}
`;

export const AXBISectionHeader = styled.div`
  ${({ theme }) => css`
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: ${theme.sizeUnit * 3}px;
    margin-bottom: ${theme.sizeUnit * 4}px;
  `}
`;

export const AXBISectionTitle = styled.h2`
  ${({ theme }) => css`
    color: ${theme.colorText};
    font-size: ${theme.fontSizeXL}px;
    font-weight: ${theme.fontWeightStrong};
    line-height: 1.3;
    margin: 0;
  `}
`;

export const AXBISectionDescription = styled.div`
  ${({ theme }) => css`
    color: ${theme.colorTextSecondary};
    line-height: 1.5;
    margin-top: ${theme.sizeUnit}px;
  `}
`;

export const AXBIQuickActionGrid = styled.div`
  ${({ theme }) => css`
    display: grid;
    gap: ${theme.sizeUnit * 3}px;
    margin-top: ${theme.sizeUnit * 4}px;
  `}
`;

export const AXBIQuickAction = styled.button`
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
      box-shadow: ${axbiSoftShadow(theme)};
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

export const AXBIEmptyCallout = styled.div`
  ${({ theme }) => css`
    border: 1px dashed ${theme.colorBorder};
    border-radius: ${theme.borderRadius}px;
    background: ${theme.colorBgContainer};
    padding: ${theme.sizeUnit * 6}px;
    text-align: center;
    margin: ${theme.sizeUnit * 5}px 0;
  `}
`;

export const AXBIEmptyCalloutTitle = styled.h2`
  ${({ theme }) => css`
    color: ${theme.colorText};
    font-size: ${theme.fontSizeXL}px;
    font-weight: ${theme.fontWeightStrong};
    margin: 0 0 ${theme.sizeUnit * 2}px;
  `}
`;

export const AXBIEmptyCalloutText = styled.p`
  ${({ theme }) => css`
    color: ${theme.colorTextSecondary};
    margin: 0 auto ${theme.sizeUnit * 4}px;
    max-width: 520px;
    line-height: 1.5;
  `}
`;

export function AXBIStat({
  label,
  value,
  hint,
}: {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
}) {
  return (
    <AXBIStatCard>
      <AXBIStatLabel>{label}</AXBIStatLabel>
      <AXBIStatValue>{value}</AXBIStatValue>
      {hint && <AXBIStatHint>{hint}</AXBIStatHint>}
    </AXBIStatCard>
  );
}

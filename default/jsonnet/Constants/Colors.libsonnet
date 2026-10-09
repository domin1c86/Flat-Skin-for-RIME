// 标签颜色常量定义
local labelColor = {
  primary: {
    light: '#000000',
    dark: '#F4F4F6',
  },
  secondary: {
    light: '#3c3c4399',
    dark: '#ebebf599',
  },
  tertiary: {
    light: '#3c3c434d',
    dark: '#ebebf54d',
  },
  quaternary: {
    light: '#3c3c432e',
    dark: '#ebebf529',
  },
};

// 分割线颜色
local separatorColor = {
  light: '#DDDFE2',
  dark: '#48494F',
};

// 扁平灰白：固定底板颜色，避免系统背景改变灰白层次。
local keyboardBackgroundColor = {
  light: '#E4E5E7',
  dark: '#1B1C1F',
};

// 标准按键背景色（如字母按键、空格键等）
local standardButtonBackgroundColor = {
  light: '#FFFFFF',
  dark: '#37383C',
};

// 标准按键按下时的背景色
local standardButtonHighlightedBackgroundColor = {
  light: '#ECEEF1',
  dark: '#51535A',
};

// 标准按键前景色（如字母按键、空格键等），用于按键的字体，图片等
local standardButtonForegroundColor = labelColor.primary;

local standardButtonHighlightedForegroundColor = standardButtonForegroundColor;

// 标准按键阴影颜色
local standardButtonShadowColor = {
  light: '#898A8D',
  dark: '#000000',
};

// 系统按键（如回车、删除等）背景颜色
local systemButtonBackgroundColor = {
  light: '#CFD0D2',
  dark: '#292A2E',
};

local systemButtonHighlightedBackgroundColor = {
  light: '#BABCC0',
  dark: '#45474E',
};

// 系统按键（如回车、删除等）前景颜色
local systemButtonForegroundColor = labelColor.primary;

local systemButtonHighlightedForegroundColor = systemButtonForegroundColor;

local blueButtonBackgroundColor = {
  light: '#007AFF',
  dark: '#0A84FF',
};

local blueButtonHighlightedBackgroundColor = { light: '#0068D9', dark: '#006BD6' };

local blueButtonForegroundColor = {
  light: '#FFFFFF',
  dark: '#FFFFFF',
};

local blueButtonHighlightedForegroundColor = {
  light: '#FFFFFF',
  dark: '#FFFFFF',
};

// 按键底部边缘颜色
local lowerEdgeOfButtonNormalColor = {
  light: '#898A8D',
  dark: '#000000',
};

// 按下状态下，按键底部边缘颜色
local lowerEdgeOfButtonHighlightColor = {
  light: '#898A8D',
  dark: '#000000',
};

// 标准按键 Hint 背景色(包含长按符号列表的背景色)
local standardCalloutBackgroundColor = standardButtonBackgroundColor;

// 标准按键 Hint 前景色，用于按键的字体，图片等
local standardCalloutForegroundColor = standardButtonForegroundColor;

local standardCalloutHighlightedForegroundColor = {
  light: '#FFFFFF',
  dark: '#FFFFFF',
};

// 标准按键 Hint 选中背景色，如长按符号列表中选中的符号背景色
local standardCalloutSelectedBackgroundColor = blueButtonBackgroundColor;

// 标准按键 Hint 边框颜色
local standardCalloutBorderColor = {
  light: '#C6C6C8',
  dark: '#69686A',
};

// 预编辑区文字颜色
local preeditForegroundColor = standardButtonForegroundColor;

// 工具栏按钮前景色
local toolbarButtonForegroundColor = { light: '#64666A', dark: '#B3B4BA' };

// 工具栏按钮高亮前景色
local toolbarButtonHighlightedForegroundColor = blueButtonBackgroundColor;

// 候选字亮候选字背景颜色
local candidateHighlightColor = standardButtonBackgroundColor;
local candidateForegroundColor = standardButtonForegroundColor;

// 候选字分隔线颜色
local candidateSeparatorColor = separatorColor;


{
  labelColor: labelColor,
  separatorColor: separatorColor,
  keyboardBackgroundColor: keyboardBackgroundColor,
  standardButtonBackgroundColor: standardButtonBackgroundColor,
  standardButtonHighlightedBackgroundColor: standardButtonHighlightedBackgroundColor,
  standardButtonForegroundColor: standardButtonForegroundColor,
  standardButtonHighlightedForegroundColor: standardButtonHighlightedForegroundColor,
  standardButtonShadowColor: standardButtonShadowColor,
  systemButtonBackgroundColor: systemButtonBackgroundColor,
  systemButtonHighlightedBackgroundColor: systemButtonHighlightedBackgroundColor,
  systemButtonForegroundColor: systemButtonForegroundColor,
  systemButtonHighlightedForegroundColor: systemButtonHighlightedForegroundColor,
  blueButtonBackgroundColor: blueButtonBackgroundColor,
  blueButtonHighlightedBackgroundColor: blueButtonHighlightedBackgroundColor,
  blueButtonForegroundColor: blueButtonForegroundColor,
  blueButtonHighlightedForegroundColor: blueButtonHighlightedForegroundColor,
  lowerEdgeOfButtonNormalColor: lowerEdgeOfButtonNormalColor,
  lowerEdgeOfButtonHighlightColor: lowerEdgeOfButtonHighlightColor,
  standardCalloutBackgroundColor: standardCalloutBackgroundColor,
  standardCalloutForegroundColor: standardCalloutForegroundColor,
  standardCalloutHighlightedForegroundColor: standardCalloutHighlightedForegroundColor,
  standardCalloutSelectedBackgroundColor: standardCalloutSelectedBackgroundColor,
  standardCalloutBorderColor: standardCalloutBorderColor,
  preeditForegroundColor: preeditForegroundColor,
  toolbarButtonForegroundColor: toolbarButtonForegroundColor,
  toolbarButtonHighlightedForegroundColor: toolbarButtonHighlightedForegroundColor,
  candidateHighlightColor: candidateHighlightColor,
  candidateForegroundColor: candidateForegroundColor,
  candidateSeparatorColor: candidateSeparatorColor,
  swipeHintColor: { light: '#97999C', dark: '#9B9DA6' },
}

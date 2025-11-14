'use client';

import React, { useState } from 'react';
import { Typography, Space, Tag } from 'antd';
import { ToolOutlined, DownOutlined, UpOutlined } from '@ant-design/icons';
import type { ToolCall } from '../types/chat';

const { Text, Paragraph } = Typography;

interface ToolCallDisplayProps {
  toolCall: ToolCall;
}

export const ToolCallDisplay: React.FC<ToolCallDisplayProps> = ({ toolCall }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mb-2 rounded-xl glass border border-white/10 p-3 transition-all hover:border-white/20 hover:shadow-lg hover:shadow-blue-500/10">
      <div
        className="flex cursor-pointer items-center justify-between transition-all duration-200 hover:text-white/90"
        onClick={() => setIsOpen(!isOpen)}
      >
        <Space>
          <ToolOutlined className="text-blue-400/90" />
          <Tag 
            color="blue" 
            className="border-blue-400/30 text-blue-300/90 bg-blue-500/10 backdrop-blur-sm"
          >
            {toolCall.tool}
          </Tag>
          <Text className="text-sm text-white/70">
            {toolCall.result ? (
              <span className="text-green-400/90">Completed</span>
            ) : (
              <span className="text-yellow-400/90">Running...</span>
            )}
          </Text>
        </Space>
        {isOpen ? (
          <UpOutlined className="text-white/60 transition-transform" />
        ) : (
          <DownOutlined className="text-white/60 transition-transform" />
        )}
      </div>

      {isOpen && (
        <div className="mt-3 space-y-3 border-t border-white/10 pt-3 animate-in fade-in slide-in-from-top-2">
          {toolCall.input ? (
            <div>
              <Text className="text-xs font-semibold text-white/60 uppercase tracking-wide">
                Input:
              </Text>
              <div className="mt-1.5 rounded-lg glass-dark p-3 border border-white/10">
                <pre className="text-xs text-white/80 overflow-x-auto font-mono">
                  {JSON.stringify(toolCall.input, null, 2)}
                </pre>
              </div>
            </div>
          ) : null}

          {toolCall.result && (
            <div>
              <Text className="text-xs font-semibold text-white/60 uppercase tracking-wide">
                Result:
              </Text>
              <div className="mt-1.5 rounded-lg glass-dark p-3 border border-white/10">
                <Paragraph className="mb-0 text-xs text-white/80 whitespace-pre-wrap wrap-break-word" copyable>
                  {toolCall.result}
                </Paragraph>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};


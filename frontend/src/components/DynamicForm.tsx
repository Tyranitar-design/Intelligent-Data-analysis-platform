import { useState, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Info } from 'lucide-react'

// 字段类型定义
interface ParamField {
  type: string
  label: string
  description?: string
  placeholder?: string
  required?: boolean
  default?: any
  min?: number
  max?: number
  options?: { value: string; label: string }[]
}

interface DynamicFormProps {
  schema: Record<string, ParamField>
  values: Record<string, any>
  onChange: (values: Record<string, any>) => void
  disabled?: boolean
}

export default function DynamicForm({ schema, values, onChange, disabled }: DynamicFormProps) {
  const handleChange = (field: string, value: any) => {
    onChange({ ...values, [field]: value })
  }

  const renderField = (fieldName: string, field: ParamField) => {
    const value = values[fieldName] ?? field.default ?? ''

    switch (field.type) {
      case 'string':
        return (
          <Input
            type="text"
            placeholder={field.placeholder || ''}
            value={value}
            onChange={(e) => handleChange(fieldName, e.target.value)}
            disabled={disabled}
            className="w-full"
          />
        )

      case 'integer':
      case 'number':
        return (
          <Input
            type="number"
            placeholder={field.placeholder || ''}
            value={value}
            min={field.min}
            max={field.max}
            onChange={(e) => {
              const val = e.target.value === '' ? '' : Number(e.target.value)
              handleChange(fieldName, val)
            }}
            disabled={disabled}
            className="w-full"
          />
        )

      case 'boolean':
        return (
          <Switch
            checked={!!value}
            onCheckedChange={(checked) => handleChange(fieldName, checked)}
            disabled={disabled}
          />
        )

      case 'enum':
        return (
          <Select
            value={String(value)}
            onValueChange={(val) => handleChange(fieldName, val)}
            disabled={disabled}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder={`选择${field.label}`} />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )

      case 'array':
        return (
          <Input
            type="text"
            placeholder={field.placeholder || '用逗号分隔多个值'}
            value={Array.isArray(value) ? value.join(',') : value}
            onChange={(e) => handleChange(fieldName, e.target.value)}
            disabled={disabled}
            className="w-full"
          />
        )

      case 'date':
        return (
          <Input
            type="date"
            value={value}
            onChange={(e) => handleChange(fieldName, e.target.value)}
            disabled={disabled}
            className="w-full"
          />
        )

      default:
        return (
          <Input
            type="text"
            placeholder={field.placeholder || ''}
            value={value}
            onChange={(e) => handleChange(fieldName, e.target.value)}
            disabled={disabled}
            className="w-full"
          />
        )
    }
  }

  return (
    <div className="space-y-4">
      {Object.entries(schema).map(([fieldName, field]) => (
        <div key={fieldName} className="space-y-2">
          <div className="flex items-center gap-2">
            <Label className="text-sm font-medium">
              {field.label}
              {field.required && (
                <Badge variant="destructive" className="ml-1 text-[10px] px-1 py-0">
                  必填
                </Badge>
              )}
            </Label>
            {field.description && (
              <div className="group relative">
                <Info className="w-3.5 h-3.5 text-muted-foreground cursor-help" />
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-50">
                  <div className="bg-popover text-popover-foreground text-xs px-2 py-1 rounded shadow-lg border whitespace-nowrap">
                    {field.description}
                  </div>
                </div>
              </div>
            )}
          </div>
          {renderField(fieldName, field)}
          {field.description && (
            <p className="text-xs text-muted-foreground">{field.description}</p>
          )}
        </div>
      ))}
    </div>
  )
}

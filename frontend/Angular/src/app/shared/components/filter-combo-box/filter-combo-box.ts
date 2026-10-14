import { Component, ElementRef, EventEmitter, HostListener, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

export interface FilterOption {
  value: string;
  label: string;
  count?: number;
  color?: string;
}

@Component({
  selector: 'app-filter-combo-box',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './filter-combo-box.html'
})
export class FilterComboBox {
  @Input() label = '';
  @Input() allLabel = 'All';
  @Input() options: FilterOption[] = [];
  @Input() selected: string | null = null;
  @Input() disabled = false;
  @Output() selectedChange = new EventEmitter<string | null>();

  open = false;
  search = '';

  constructor(private host: ElementRef<HTMLElement>) {}

  get selectedOption(): FilterOption | null {
    return this.options.find(o => o.value === this.selected) ?? null;
  }

  get filteredOptions(): FilterOption[] {
    const term = this.search.trim().toLowerCase();
    return term
      ? this.options.filter(o => o.label.toLowerCase().includes(term))
      : this.options;
  }

  toggle() {
    if (this.disabled) return;
    this.open = !this.open;
    this.search = '';
  }

  select(value: string | null) {
    this.selected = value;
    this.selectedChange.emit(value);
    this.open = false;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event) {
    if (!this.host.nativeElement.contains(event.target as Node)) {
      this.open = false;
    }
  }
}